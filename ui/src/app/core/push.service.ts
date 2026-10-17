import { Injectable, computed, inject, signal } from '@angular/core';
import { Capacitor, registerPlugin } from '@capacitor/core';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';

/** Mirrors the native permission states; 'unsupported' is the web build. */
export type PushPermission = 'prompt' | 'granted' | 'denied' | 'unsupported';

/**
 * Settings screen ids → backend NotificationPreference categories
 * (astrospace/db/crud_mobile.py DEFAULT_NOTIFICATION_PREFS). One mapping,
 * one place; the screen never learns the backend names.
 */
export const PREF_CATEGORY: Record<string, string> = {
  morning: 'morning_brief',
  windows: 'window_alert',
  festivals: 'festival_reminder',
  remedies: 'remedy_reminder',
};

const TOKEN_KEY = 'astrospace.push.token';

/** Native check in ui/android/.../PushConfigPlugin.java. Android only. */
const PushConfig = registerPlugin<{ available(): Promise<{ available: boolean }> }>('PushConfig');

/** Shown in settings when the build has no Firebase config to register with. */
export const PUSH_NOT_CONFIGURED = 'Push notifications are not set up in this build of the app yet.';

/**
 * Device push registration, end to end on the client side.
 *
 * On a native platform with permission granted, `register()` asks the OS for
 * a token and PUTs it to /me/push-tokens with the provider the platform
 * uses (FCM on Android, APNs on iOS). The token is remembered so sign-out can
 * revoke exactly the one this device registered: a signed-out phone must not
 * keep receiving the previous account's morning brief.
 *
 * Nothing here runs on web. The web app has no service worker and the
 * backend has no web-push transport, so `permission()` reports 'unsupported'
 * and the settings screen says so rather than offering a button that cannot
 * deliver.
 */
@Injectable({ providedIn: 'root' })
export class PushService {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);

  readonly permission = signal<PushPermission>(Capacitor.isNativePlatform() ? 'prompt' : 'unsupported');
  readonly registered = signal(false);
  readonly error = signal<string | null>(null);
  readonly native = computed(() => Capacitor.isNativePlatform());

  private listenersInstalled = false;

  /** Called once after auth resolves on native boot. Never prompts. */
  async init(): Promise<void> {
    if (!this.native()) return;
    await this.refreshPermission();
    if (this.permission() === 'granted' && this.auth.isAuthenticated()) {
      await this.register();
    }
  }

  async refreshPermission(): Promise<PushPermission> {
    if (!this.native()) return 'unsupported';
    try {
      const { PushNotifications } = await import('@capacitor/push-notifications');
      const { receive } = await PushNotifications.checkPermissions();
      this.permission.set(receive === 'prompt-with-rationale' ? 'prompt' : receive);
    } catch (err) {
      this.error.set(describe(err));
    }
    return this.permission();
  }

  /**
   * The one place the OS prompt is shown: from the settings screen, when the
   * reader taps "Turn on notifications". Opt-in, never on launch.
   */
  async enable(): Promise<PushPermission> {
    if (!this.native()) return 'unsupported';
    try {
      const { PushNotifications } = await import('@capacitor/push-notifications');
      const { receive } = await PushNotifications.requestPermissions();
      this.permission.set(receive === 'prompt-with-rationale' ? 'prompt' : receive);
      if (receive === 'granted') await this.register();
    } catch (err) {
      this.error.set(describe(err));
    }
    return this.permission();
  }

  /** Asks the OS for a token and hands it to the API. Resolves when stored. */
  async register(): Promise<void> {
    if (!this.native()) return;
    this.error.set(null);
    if (!(await pushConfigured())) {
      this.error.set(PUSH_NOT_CONFIGURED);
      return;
    }
    try {
      const { PushNotifications } = await import('@capacitor/push-notifications');
      await this.installListeners(PushNotifications);
      await PushNotifications.register();
    } catch (err) {
      this.error.set(describe(err));
    }
  }

  /** Sign-out path: tell the API this device no longer speaks for the account. */
  async revoke(): Promise<void> {
    const token = readToken();
    if (!token) return;
    try {
      await this.api.post('/me/push-tokens/revoke', token);
    } catch {
      // Best effort: the backend also revokes a token the provider reports dead.
    } finally {
      try { localStorage.removeItem(TOKEN_KEY); } catch { /* storage unavailable */ }
      this.registered.set(false);
    }
  }

  /** Preference toggles go to the server too, so the worker can honour them. */
  async syncPreference(id: string, on: boolean): Promise<void> {
    const category = PREF_CATEGORY[id];
    if (!category || !this.auth.isAuthenticated()) return;
    try {
      await this.api.put(`/me/notification-preferences/${category}`, { enabled: on });
    } catch {
      // Local state is already saved; the next toggle retries.
    }
  }

  /**
   * The account's saved switches, keyed by the screen's ids. The server is the
   * record the worker reads, so a reinstall or a second phone shows what the
   * account actually gets rather than the defaults.
   */
  async loadPreferences(): Promise<Record<string, boolean> | null> {
    if (!this.auth.isAuthenticated()) return null;
    try {
      const { preferences } = await this.api.get<{ preferences: Record<string, { enabled?: boolean }> }>(
        '/me/notification-preferences',
      );
      const out: Record<string, boolean> = {};
      for (const [id, category] of Object.entries(PREF_CATEGORY)) {
        const enabled = preferences[category]?.enabled;
        if (typeof enabled === 'boolean') out[id] = enabled;
      }
      return out;
    } catch {
      return null;
    }
  }

  /** Opens the app's own notification settings when permission was denied. */
  async openSystemSettings(): Promise<void> {
    if (!this.native()) return;
    try {
      const { NativeSettings, AndroidSettings, IOSSettings } = await import('capacitor-native-settings');
      await NativeSettings.open({
        optionAndroid: AndroidSettings.AppNotification,
        optionIOS: IOSSettings.AppNotification,
      });
    } catch (err) {
      this.error.set(describe(err));
    }
  }

  private async installListeners(plugin: typeof import('@capacitor/push-notifications').PushNotifications): Promise<void> {
    if (this.listenersInstalled) return;
    this.listenersInstalled = true;
    await plugin.addListener('registration', ({ value }) => void this.storeToken(value));
    await plugin.addListener('registrationError', ({ error }) => {
      this.error.set(error || 'The device did not return a push token.');
      this.registered.set(false);
    });
  }

  private async storeToken(value: string): Promise<void> {
    const provider = Capacitor.getPlatform() === 'ios' ? 'apns' : 'fcm';
    const registration = {
      provider,
      token: value,
      environment: 'production',
      locale: navigator.language,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    };
    try {
      await this.api.put('/me/push-tokens', registration);
      try { localStorage.setItem(TOKEN_KEY, JSON.stringify({ provider, token: value })); } catch { /* storage unavailable */ }
      this.registered.set(true);
    } catch (err) {
      this.error.set(describe(err));
      this.registered.set(false);
    }
  }
}

/**
 * An Android build without google-services.json has no FirebaseApp, and the
 * push plugin's register() then crashes the process on a native thread that
 * no try/catch here can reach. Ask natively first. iOS registers with APNs
 * and has no such failure, so it is always considered configured.
 */
async function pushConfigured(): Promise<boolean> {
  if (Capacitor.getPlatform() !== 'android') return true;
  try {
    return (await PushConfig.available()).available;
  } catch {
    return false;
  }
}

function readToken(): { provider: string; token: string } | null {
  try {
    const raw = localStorage.getItem(TOKEN_KEY);
    return raw ? (JSON.parse(raw) as { provider: string; token: string }) : null;
  } catch {
    return null;
  }
}

function describe(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}
