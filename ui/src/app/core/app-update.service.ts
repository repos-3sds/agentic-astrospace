import { Injectable, computed, inject, signal } from '@angular/core';
import { Capacitor, registerPlugin } from '@capacitor/core';
import { ApiService } from './api.service';

/** What the server says about this build (astrospace/notifications/app_updates.py). */
export interface AppVersionStatus {
  platform: 'android' | 'ios';
  build: number;
  status: 'current' | 'update_available' | 'update_required';
  latest_build: number | null;
  required_build: number | null;
  update_url: string;
}

/** Native in ui/android/.../InAppUpdatePlugin.java: Play's own update screen. Android only. */
interface InAppUpdatePlugin {
  check(): Promise<{ available: boolean; versionCode?: number; immediate?: boolean }>;
  start(): Promise<{ started: boolean }>;
}
const InAppUpdate = registerPlugin<InAppUpdatePlugin>('InAppUpdate');

const SNOOZE_KEY = 'siddha.update.snoozedUntil';
/** "Later" puts the sheet away for a day; the reminder pushes keep their own pace. */
export const SNOOZE_MS = 24 * 60 * 60 * 1000;
/** Coming back to the front looks again, but not more often than this. */
const RECHECK_MS = 10 * 60 * 1000;

let buildNumber: Promise<number | null> | null = null;

/**
 * This install's build number (versionCode on Android, CFBundleVersion on
 * iOS; both are the commit count on main). Null on web, where the page is
 * always the newest.
 */
export function appBuild(): Promise<number | null> {
  if (!Capacitor.isNativePlatform()) return Promise.resolve(null);
  buildNumber ??= import('@capacitor/app')
    .then(({ App }) => App.getInfo())
    .then((info) => {
      const n = Number.parseInt(info.build, 10);
      return Number.isFinite(n) && n > 0 ? n : null;
    })
    .catch(() => null);
  return buildNumber;
}

/**
 * Asks the server on every launch, and on coming back to the front, whether
 * this build is still the one to have (Hawk, 2026-10-29: remind readers on
 * an old build until they update, and restrict the app until they do).
 *
 * - `update_available`: a sheet with Update and Later. Later hides it for a
 *   day. On Android it shows only once Play itself has the update for this
 *   reader, so nobody is sent to a store page with no Update button.
 * - `update_required`: a full-screen page with one button, and nothing else
 *   in the app can be used. Only when Hawk marks a build required (or sets a
 *   grace period) for the platform; never on its own.
 *
 * A failed check changes nothing: an offline reader keeps using the app.
 */
@Injectable({ providedIn: 'root' })
export class AppUpdateService {
  private readonly api = inject(ApiService);

  readonly status = signal<AppVersionStatus | null>(null);
  /** Play has the update ready for this reader (Android); null when Play could not say. */
  private readonly playHasIt = signal<boolean | null>(null);
  private readonly snoozed = signal(isSnoozed());
  private checkedAt = 0;
  private started = false;

  readonly blocked = computed(() => this.status()?.status === 'update_required');
  readonly offer = computed(() => {
    const s = this.status();
    if (s?.status !== 'update_available' || this.snoozed()) return false;
    return this.playHasIt() !== false;
  });
  readonly store = computed(() => (this.status()?.platform === 'ios' ? 'TestFlight' : 'Google Play'));

  start(): void {
    if (this.started || !Capacitor.isNativePlatform()) return;
    this.started = true;
    void this.check(true);
    void import('@capacitor/app')
      .then(({ App }) => App.addListener('appStateChange', ({ isActive }) => {
        if (isActive) void this.check(false);
      }))
      .catch(() => undefined);
  }

  async check(force: boolean): Promise<void> {
    const now = Date.now();
    // A blocked app looks every time it comes back: the reader may have updated.
    if (!force && !this.blocked() && now - this.checkedAt < RECHECK_MS) return;
    this.checkedAt = now;
    const build = await appBuild();
    const platform = Capacitor.getPlatform();
    if (build === null || (platform !== 'android' && platform !== 'ios')) return;
    try {
      const status = await this.api.get<AppVersionStatus>(`/app/version?platform=${platform}&build=${build}`);
      this.status.set(status);
      this.snoozed.set(isSnoozed());
      if (platform === 'android' && status.status !== 'current') {
        this.playHasIt.set(await playHasUpdate());
      }
    } catch {
      /* offline or the server is busy: carry on as before */
    }
  }

  /** Update: Play's own update screen on Android, else the store link. */
  async update(): Promise<void> {
    const s = this.status();
    if (!s) return;
    if (s.platform === 'android' && this.playHasIt()) {
      try {
        if ((await InAppUpdate.start()).started) return;
      } catch { /* fall through to the listing */ }
    }
    try {
      window.open(s.update_url, '_system');
    } catch { /* nothing more to try; the button stays */ }
  }

  later(): void {
    try { localStorage.setItem(SNOOZE_KEY, String(Date.now() + SNOOZE_MS)); } catch { /* hidden for this visit only */ }
    this.snoozed.set(true);
  }
}

async function playHasUpdate(): Promise<boolean | null> {
  try {
    return (await InAppUpdate.check()).available;
  } catch {
    return null; // a build without the plugin, or Play unreachable: trust the server
  }
}

function isSnoozed(): boolean {
  try {
    return Number(localStorage.getItem(SNOOZE_KEY) ?? 0) > Date.now();
  } catch {
    return false;
  }
}
