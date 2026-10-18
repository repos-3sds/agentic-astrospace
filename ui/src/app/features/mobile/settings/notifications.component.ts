import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { PushService } from '../../../core/push.service';
import { EmailCategory, EmailSettingsService } from '../../../core/email-settings.service';
import { BackLinkDirective } from '../../../core/back-link.directive';

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
 *
 * Delivery has three states, and the screen names each one honestly:
 * - prompt: nothing asked yet. One button shows the OS dialog, here and only
 *   here, never on launch.
 * - denied: the OS said no. The app cannot ask again, so the card says where
 *   the switch lives and opens it; "Remind me later" is the other way out.
 * - granted: this device is registered and the worker delivers to it.
 * On web there is no push at all, and the card says that rather than offering
 * a button that cannot deliver.
 *
 * Email is a separate section with its own switches, both off by default,
 * and works on web too. Its state lives on the server, because every email
 * carries a link that can turn it off.
 */
@Component({
  selector: 'as-settings-notifications',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackLinkDirective],
  templateUrl: './notifications.component.html',
  styleUrl: './notifications.component.scss',
})
export class NotificationsComponent {
  private readonly push = inject(PushService);
  private readonly storageKey = 'astrospace.mobile.notificationPrefs';
  private readonly snoozeKey = 'astrospace.mobile.notificationPrompt.snoozedUntil';
  private readonly defaults: NotificationPref[] = [
    { id: 'morning', title: 'Morning brief', detail: 'Your day, every morning', on: true },
    // Off until a Sanskrit scholar has read the verses (docs/subhashita_corpus.md).
    { id: 'subhashita', title: 'Today’s Subhashita', detail: 'A verse from the Gita, Chanakya Niti and the Puranas, at 10 am', on: false },
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
  readonly permission = this.push.permission;
  readonly registered = this.push.registered;
  readonly pushError = this.push.error;
  readonly nativeApp = this.push.native;
  readonly busy = signal(false);
  readonly snoozed = signal(this.isSnoozed());

  private readonly emailSettings = inject(EmailSettingsService);
  readonly email = this.emailSettings.state;
  readonly emailError = this.emailSettings.error;
  readonly emailRows: { id: EmailCategory; title: string; detail: string }[] = [
    { id: 'daily_email', title: 'Daily reading', detail: 'Your day, in your inbox each morning' },
    {
      id: 'festival_email',
      title: 'Moon and festival days',
      detail: 'Full moon, new moon and festivals, the evening before',
    },
  ];

  /** Headline of the delivery card, one per state. */
  readonly deliveryTitle = computed(() => {
    switch (this.permission()) {
      case 'granted': return 'Notifications are on';
      case 'denied': return 'Notifications are off for Siddha';
      case 'unsupported': return 'Not available on the web';
      default: return 'Notifications are off';
    }
  });

  readonly deliveryState = computed(() => {
    switch (this.permission()) {
      // Whether the token has reached the server yet is plumbing, not news:
      // the screen re-registers on open and shows an error only if that fails.
      case 'granted':
        return 'Your choices below decide what arrives. Nothing is sent that you did not turn on.';
      case 'denied':
        return 'The system switch for this app is off, so nothing can be delivered until you turn it on in Settings. Your choices here are kept for when you do.';
      case 'unsupported':
        return 'Push delivery is a feature of the Siddha app on your phone. Your choices are saved for it.';
      default:
        return 'Turn them on to get your morning brief and the alerts you choose. You will be asked once by the system.';
    }
  });

  /** What the Settings hub reports as "N on" — derived, never stated twice. */
  readonly onCount = computed(() => this.prefs().filter((p) => p.on).length);

  constructor() {
    if (this.nativeApp()) void this.recheck();
    void this.emailSettings.load();
    void this.loadAccountPrefs();
  }

  /** Switches saved on the account win over this device's copy. */
  private async loadAccountPrefs(): Promise<void> {
    const saved = await this.push.loadPreferences();
    if (!saved) return;
    this.prefs.update((prefs) => prefs.map((p) => ({ ...p, on: saved[p.id] ?? p.on })));
    this.persist();
  }

  protected toggleEmail(id: EmailCategory): void {
    const state = this.email();
    if (!state) return;
    void this.emailSettings.set(id, !state.categories[id]);
  }

  protected toggle(id: string): void {
    this.prefs.update((prefs) =>
      prefs.map((p) => (p.id === id ? { ...p, on: !p.on } : p)),
    );
    this.persist();
    const pref = this.prefs().find((p) => p.id === id);
    if (pref) void this.push.syncPreference(id, pref.on);
  }

  /** The one place the OS prompt is shown. */
  protected async enable(): Promise<void> {
    this.busy.set(true);
    try {
      await this.push.enable();
    } finally {
      this.busy.set(false);
    }
  }

  protected async openSettings(): Promise<void> {
    await this.push.openSystemSettings();
  }

  /** The way out of the denied card that is not "go change a system setting". */
  protected remindLater(): void {
    const until = Date.now() + 7 * 24 * 60 * 60 * 1000;
    try { localStorage.setItem(this.snoozeKey, String(until)); } catch { /* storage unavailable */ }
    this.snoozed.set(true);
  }

  /** Permission can change in system settings while the app is backgrounded. */
  protected async recheck(): Promise<void> {
    await this.push.refreshPermission();
    if (this.permission() === 'granted' && !this.registered()) await this.push.register();
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

  private isSnoozed(): boolean {
    try {
      return Number(localStorage.getItem(this.snoozeKey) ?? 0) > Date.now();
    } catch {
      return false;
    }
  }
}
