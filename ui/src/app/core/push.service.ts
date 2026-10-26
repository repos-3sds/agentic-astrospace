import { Injectable, computed, effect, inject, signal, untracked } from '@angular/core';
import { Router } from '@angular/router';
import { Capacitor, registerPlugin } from '@capacitor/core';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';
import { noteDeepLink } from './deep-link-arrival';

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
  subhashita: 'daily_subhashita',
};

const TOKEN_KEY = 'astrospace.push.token';

/**
 * A request answered faster than this came back without the system dialog
 * ever showing: Android after a second "Don't allow" (or a dismissed dialog,
 * which Capacitor records as denied), iOS after any earlier no. A person
 * tapping a button in a dialog takes well over half a second.
 */
const NO_DIALOG_MS = 600;

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
  private readonly router = inject(Router);

  readonly permission = signal<PushPermission>(Capacitor.isNativePlatform() ? 'prompt' : 'unsupported');
  readonly registered = signal(false);
  readonly error = signal<string | null>(null);
  readonly native = computed(() => Capacitor.isNativePlatform());

  private listenersInstalled = false;
  private askedThisLaunch = false;
  private booted = false;
  private signedInAs: string | null = null;

  constructor() {
    // Boot registers whoever is signed in at launch. Signing out and back in
    // without a restart left the device with no live token until the next
    // cold start (retest of build 487), so a new sign-in registers again.
    effect(() => {
      const userId = this.auth.session()?.user?.id ?? null;
      untracked(() => {
        if (userId && userId !== this.signedInAs && this.booted) void this.init();
        this.signedInAs = userId;
      });
    });
    // Coming back from the phone's settings is how a denied reader turns
    // notifications on, so look again whenever the app comes to the front.
    // Before this the screen still said "off" until it was reopened.
    if (this.native()) {
      void import('@capacitor/app')
        .then(({ App }) => App.addListener('appStateChange', ({ isActive }) => {
          if (isActive && this.booted) void this.init();
        }))
        .catch(() => undefined);
    }
  }

  /**
   * Called after auth resolves on native boot, on each later sign-in and
   * whenever the app comes back to the front. Registers the device if
   * notifications are allowed; if the reader has not answered the system
   * question yet, asks it, once per launch.
   */
  async init(): Promise<void> {
    this.booted = true;
    if (!this.native()) return;
    await this.refreshPermission();
    if (!this.auth.isAuthenticated()) return;
    if (this.permission() === 'granted') {
      await this.register();
    } else if (this.permission() === 'prompt' && !this.askedThisLaunch) {
      await this.askOnLaunch();
    }
  }

  /**
   * The system question when the app opens (Hawk, 2026-10-20: testers never
   * found the switch in Settings, and without notifications nobody comes
   * back). Only while unanswered: after a no, Android shows it once more on a
   * later launch and then stops on its own, and iOS never shows it twice.
   * Never sends anyone to Settings uninvited; that is the button's job.
   */
  private async askOnLaunch(): Promise<void> {
    this.askedThisLaunch = true;
    try {
      const { PushNotifications } = await import('@capacitor/push-notifications');
      const { receive } = await PushNotifications.requestPermissions();
      this.permission.set(receive === 'prompt-with-rationale' ? 'prompt' : receive);
      if (receive === 'granted') await this.register();
    } catch (err) {
      this.error.set(describe(err));
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
   * "Turn on notifications", wherever it is offered (the Today card and
   * Settings > Notifications). Asks the system first, every
   * time: Capacitor records a dismissed dialog as denied although Android
   * will still show it again. If the system answers without showing its
   * dialog, the reader cannot be asked from inside the app any more, so this
   * opens Siddha's page in the phone's notification settings instead of
   * doing nothing (tester report on build 537).
   */
  async enable(): Promise<PushPermission> {
    if (!this.native()) return 'unsupported';
    const before = this.permission();
    try {
      const { PushNotifications } = await import('@capacitor/push-notifications');
      const started = Date.now();
      const { receive } = await PushNotifications.requestPermissions();
      const state: PushPermission = receive === 'prompt-with-rationale' ? 'prompt' : receive;
      this.permission.set(state);
      if (state === 'granted') {
        if (this.auth.isAuthenticated()) await this.register();
      } else if (before === 'denied' || Date.now() - started < NO_DIALOG_MS) {
        await this.openSystemSettings();
      }
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
   * Queues a test push for this account. The server hands it to the same
   * worker as every real notification, so it arriving proves the whole path;
   * the worker runs every 15 minutes. Resolves to what the screen should say.
   */
  async sendTest(): Promise<string> {
    try {
      await this.api.post('/me/test-notification', {});
      return 'Test queued. It reaches this phone within 15 minutes.';
    } catch (err) {
      const status = (err as { status?: number })?.status;
      if (status === 409) return 'This phone isn’t registered for notifications yet. Close and reopen Siddha, then try again.';
      return 'Couldn’t queue the test. Check your connection and try again.';
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
    // A tapped push opens the screen it is about (the worker sets deep_link,
    // e.g. /m/subhashita). Only in-app paths: the data is server-written, but
    // the app never follows a push off to the web.
    await plugin.addListener('pushNotificationActionPerformed', ({ notification }) => {
      const link = (notification.data as Record<string, unknown> | undefined)?.['deep_link'];
      if (typeof link === 'string' && link.startsWith('/m/')) {
        noteDeepLink();
        void this.router.navigateByUrl(link);
      }
    });
    await plugin.addListener('registrationError', ({ error }) => {
      this.error.set(error || 'The device did not return a push token.');
      this.registered.set(false);
    });
  }

  private async storeToken(value: string): Promise<void> {
    const provider = Capacitor.getPlatform() === 'ios' ? 'apns' : 'fcm';
    let previous: string | undefined;
    try {
      const stored = JSON.parse(localStorage.getItem(TOKEN_KEY) ?? 'null') as { provider?: string; token?: string } | null;
      if (stored?.provider === provider && stored.token && stored.token !== value) previous = stored.token;
    } catch { /* storage unavailable or unreadable */ }
    const registration = {
      provider,
      token: value,
      // The OS rotated this device's token: retire the old one, or each push
      // reaches the phone twice.
      ...(previous ? { replaces: previous } : {}),
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
