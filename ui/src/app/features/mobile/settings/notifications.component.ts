import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import { RouterLink } from '@angular/router';

/** One thing the app may notify about. */
export interface NotificationPref {
  id: string;
  title: string;
  detail: string;
  on: boolean;
}

/**
 * Settings — Notifications (Figma node 67:173).
 *
 * "Opt-in, never fear-based" is the lede and it is also the design rule. None
 * of these is an alarm: a window alert says a window is coming, not that
 * something bad will happen in it. An astrology app that can push notifications
 * is one keystroke away from monetising dread, so what it will not send belongs
 * on the screen where you choose what it does.
 *
 * Remedy reminders default off. A practice someone chose is theirs to remember;
 * nagging about a streak is how a practice becomes a debt — the same reason the
 * mantra tracker never warns about breaking one.
 */
@Component({
  selector: 'as-settings-notifications',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './notifications.component.html',
  styleUrl: './notifications.component.scss',
})
export class NotificationsComponent {
  private readonly storageKey = 'astrospace.mobile.notificationPrefs';
  private readonly defaults: NotificationPref[] = [
    { id: 'morning', title: 'Morning brief', detail: 'Your day, every morning', on: true },
    {
      id: 'windows',
      title: 'Window alerts',
      detail: 'Before Rahu Kalam and other windows',
      on: true,
    },
    {
      id: 'festivals',
      title: 'Festival reminders',
      detail: 'A few days ahead of observances',
      on: true,
    },
    {
      id: 'remedies',
      title: 'Remedy reminders',
      detail: 'For streaks and scheduled practices',
      on: false,
    },
  ];

  readonly prefs = signal<NotificationPref[]>(this.restorePrefs());
  readonly permission = signal(this.notificationPermission());
  readonly pushAvailable = computed(() => typeof Notification !== 'undefined');
  readonly nativeApp = computed(() => Capacitor.isNativePlatform());
  readonly deliveryState = computed(() => {
    if (!this.pushAvailable()) {
      return this.nativeApp()
        ? 'Push delivery is not enabled in this build yet. Your choices are saved for the native notification service.'
        : 'Push delivery is not enabled in this web session. Your choices are saved for the native app.';
    }
    if (this.permission() === 'denied') return 'Notifications are blocked for this app. Enable them in Android settings when push delivery is connected.';
    if (this.permission() === 'granted') return 'Preferences are saved locally. Device-token delivery still requires the native push service.';
    return 'Preferences are saved locally. Permission can be requested once native push delivery is connected.';
  });

  /** What the Settings hub reports as "N on" — derived, never stated twice. */
  readonly onCount = computed(() => this.prefs().filter((p) => p.on).length);

  protected toggle(id: string): void {
    this.prefs.update((prefs) =>
      prefs.map((p) => (p.id === id ? { ...p, on: !p.on } : p)),
    );
    this.persist();
  }

  protected async requestPermission(): Promise<void> {
    if (typeof Notification === 'undefined' || !Notification.requestPermission) return;
    this.permission.set(await Notification.requestPermission());
  }

  private restorePrefs(): NotificationPref[] {
    try {
      const stored = JSON.parse(localStorage.getItem(this.storageKey) ?? '[]') as Partial<NotificationPref>[];
      return this.defaults.map((pref) => ({ ...pref, on: stored.find((row) => row.id === pref.id)?.on ?? pref.on }));
    } catch {
      return this.defaults;
    }
  }

  private persist(): void {
    localStorage.setItem(this.storageKey, JSON.stringify(this.prefs().map(({ id, on }) => ({ id, on }))));
  }

  private notificationPermission(): NotificationPermission | 'unsupported' {
    return typeof Notification === 'undefined' ? 'unsupported' : Notification.permission;
  }
}
