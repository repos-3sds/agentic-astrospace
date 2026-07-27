import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';
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
  readonly prefs = signal<NotificationPref[]>([
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
  ]);

  /** What the Settings hub reports as "N on" — derived, never stated twice. */
  readonly onCount = computed(() => this.prefs().filter((p) => p.on).length);

  protected toggle(id: string): void {
    this.prefs.update((prefs) =>
      prefs.map((p) => (p.id === id ? { ...p, on: !p.on } : p)),
    );
  }
}
