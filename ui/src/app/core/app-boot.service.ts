import { Injectable, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Capacitor } from '@capacitor/core';

import { AuthService } from './auth.service';
import { KundliStore } from './kundli.store';
import { PreferencesService } from './preferences.service';
import { PanchangAlarmService } from './panchang-alarm.service';
import { RemedyReminderService } from './remedy-reminder.service';
import { PushService } from './push.service';

/**
 * What has to happen before the first screen can be shown, and nothing more.
 *
 * Before 2026-10-15 the root component ran, serially and with no timeouts:
 * the SQLCipher open (app initializer), /auth/config network-first, the
 * session refresh, /settings, then /kundlis. A slow network left the splash
 * up for as long as the slowest of those took. Now:
 *
 * - /auth/config comes from the device and is revalidated behind (AuthService);
 * - the session refresh is bounded (AuthService);
 * - /settings syncs in the background — preferences already persisted on the
 *   device are what the first screen renders with;
 * - /kundlis is cache-first (KundliStore), and every API read is bounded and
 *   retried once (http-resilience.interceptor).
 */
@Injectable({ providedIn: 'root' })
export class AppBootService {
  private readonly auth = inject(AuthService);
  private readonly store = inject(KundliStore);
  private readonly prefs = inject(PreferencesService);
  private readonly push = inject(PushService);
  private readonly alarms = inject(PanchangAlarmService);
  private readonly remedyReminders = inject(RemedyReminderService);
  private readonly router = inject(Router);

  /** Why boot failed, for whichever shell is on screen to say so; null while fine. */
  readonly error = signal<string | null>(null);

  async run(): Promise<void> {
    this.error.set(null);
    try {
      await this.auth.init();
      if (!this.auth.isAuthenticated()) return;
      // Re-registers the device token if permission was granted earlier,
      // or asks the system question if it has not been answered yet.
      void this.push.init();
      if (Capacitor.isNativePlatform() && this.router.url.split('?')[0] === '/m/start') {
        await this.router.navigateByUrl('/m');
      }
      if (this.auth.enabled() && this.auth.session()) {
        // Not awaited: the first render must not wait on /settings.
        void this.prefs.syncCloud().catch(() => undefined);
      }
      await this.store.load();
      // Tops up the fortnight of panchang alarms on the phone.
      void this.alarms.init();
      void this.remedyReminders.init();
    } catch (e) {
      this.error.set((e as Error)?.message || 'Could not load your profiles.');
    }
  }
}
