import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { PushService } from '../../../core/push.service';
import { RemedyReminderService } from '../../../core/remedy-reminder.service';
import { EmailCategory, EmailSettingsService } from '../../../core/email-settings.service';
import { RouterLink } from '@angular/router';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { SubhashitaService } from '../../../core/subhashita.service';
import { StickyBarDirective } from '../shared/sticky-bar.directive';

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
 * Timing alerts (Rahu Kalam, Brahma Muhurta and the rest) moved to Panchang
 * alarms, which the phone schedules itself; this screen links there.
 *
 * Remedy reminders default off. A practice someone chose is theirs to remember;
 * nagging about a streak is how a practice becomes a debt — the same reason the
 * mantra tracker never warns about breaking one.
 *
 * Delivery has three states, and the screen names each one honestly:
 * - prompt: not answered yet. The app asks once per launch (PushService.init),
 *   and the button here shows the OS dialog too.
 * - denied: the OS said no. The same button tries the dialog once more and,
 *   when the system will not show it, opens Siddha's notification settings;
 *   "Remind me later" is the other way out.
 * - granted: this device is registered and the worker delivers to it.
 * On web there is no push at all, and the card says that rather than offering
 * a button that cannot deliver.
 *
 * Email is a separate section with its own switches, all off until the reader
 * says yes (the sign-up box turns them all on), and works on web too. Its state lives on the server, because every email
 * carries a link that can turn it off.
 */
@Component({
  selector: 'as-settings-notifications',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [StickyBarDirective, BackLinkDirective, RouterLink],
  templateUrl: './notifications.component.html',
  styleUrl: './notifications.component.scss',
})
export class NotificationsComponent {
  private readonly push = inject(PushService);
  private readonly remedyReminders = inject(RemedyReminderService);
  protected readonly verse = inject(SubhashitaService);
  private readonly storageKey = 'astrospace.mobile.notificationPrefs';
  private readonly snoozeKey = 'astrospace.mobile.notificationPrompt.snoozedUntil';
  private readonly defaults: NotificationPref[] = [
    { id: 'morning', title: 'Morning brief', detail: 'Your day, every morning', on: true },
    // Off until a Sanskrit scholar has read the verses (docs/subhashita_corpus.md).
    { id: 'subhashita', title: 'Today’s Subhashita', detail: 'A verse from the Gita, Chanakya Niti and the Puranas, at 10 am', on: false },
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
    { id: 'weekly_email', title: 'Weekly outlook', detail: 'Your week ahead, every Monday morning' },
    { id: 'monthly_email', title: 'Monthly outlook', detail: 'The month ahead, on the 1st' },
    { id: 'lessons_email', title: 'Learn your chart', detail: 'Eight short lessons from your own chart' },
    { id: 'tips_email', title: 'Tips and reminders', detail: 'Features worth trying, and what is coming up' },
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
        return 'Your phone is blocking notifications from Siddha. Tap the button and turn on Allow notifications. Your choices here are kept.';
      case 'unsupported':
        return 'Push delivery is a feature of the Siddha app on your phone. Your choices are saved for it.';
      default:
        return 'Turn them on to get your morning brief and the alerts you choose.';
    }
  });

  /** What the Settings hub reports as "N on" — derived, never stated twice. */
  readonly onCount = computed(() => this.prefs().filter((p) => p.on).length);

  constructor() {
    if (this.nativeApp()) void this.recheck();
    void this.emailSettings.load();
    void this.loadAccountPrefs();
  }

  /** Switches tapped on this screen; the account's copy is older for these. */
  private readonly tapped = new Set<string>();

  /**
   * Switches saved on the account win over this device's copy, except one
   * the reader has already tapped while the answer was on its way.
   */
  private async loadAccountPrefs(): Promise<void> {
    const saved = await this.push.loadPreferences();
    if (!saved) return;
    this.prefs.update((prefs) =>
      prefs.map((p) => (this.tapped.has(p.id) ? p : { ...p, on: saved[p.id] ?? p.on })),
    );
    this.persist();
  }

  protected toggleEmail(id: EmailCategory): void {
    const state = this.email();
    if (!state) return;
    void this.emailSettings.set(id, !state.categories[id]);
  }

  protected toggle(id: string): void {
    this.tapped.add(id);
    this.prefs.update((prefs) =>
      prefs.map((p) => (p.id === id ? { ...p, on: !p.on } : p)),
    );
    this.persist();
    const pref = this.prefs().find((p) => p.id === id);
    if (pref) void this.push.syncPreference(id, pref.on);
    // Remedy reminders are scheduled on the phone, where the practice lives.
    if (id === 'remedies') void this.remedyReminders.reschedule();
  }

  /** Shows the OS prompt, or opens the phone's settings when it will not show. */
  protected async enable(): Promise<void> {
    this.busy.set(true);
    try {
      await this.push.enable();
    } finally {
      this.busy.set(false);
    }
  }

  /** What the last "Send a test notification" tap came back with. */
  readonly testNote = signal<string | null>(null);

  protected async sendTest(): Promise<void> {
    this.busy.set(true);
    try {
      this.testNote.set(await this.push.sendTest());
    } finally {
      this.busy.set(false);
    }
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
