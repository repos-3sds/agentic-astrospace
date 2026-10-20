import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { AuthService } from '../../../core/auth.service';
import { PushService } from '../../../core/push.service';

const SNOOZE_KEY = 'astrospace.mobile.notifyNudge.snoozedUntil';
const DISMISS_COUNT_KEY = 'astrospace.mobile.notifyNudge.dismissals';
const SNOOZE_MS = 7 * 24 * 60 * 60 * 1000;
/** After this many "Not now"s the card stops coming back; Settings still has the switch. */
const MAX_DISMISSALS = 3;

/**
 * "Get your reading each morning", on Today, while this phone is not
 * receiving notifications. The app also asks the system question on launch
 * (PushService.init), but after a no that question cannot be asked again,
 * and the switch in Settings > Notifications was too far away for testers
 * to find (build 537). One tap here shows the system dialog, or opens
 * Siddha's page in the phone's notification settings when Android or iOS
 * will not show it.
 *
 * Calm on purpose: it says what arrives, not what will be missed.
 */
@Component({
  selector: 'as-notify-nudge',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (visible()) {
      <section class="nudge" aria-labelledby="notify-nudge-title">
        <span class="nudge-icon" aria-hidden="true"><img src="mobile/set-notif.svg" alt="" /></span>
        <div class="nudge-text">
          <p class="nudge-title" id="notify-nudge-title">Get your reading each morning</p>
          <p class="nudge-detail">A short note with your day, and a heads-up before good times. You choose what comes.</p>
          <div class="nudge-actions">
            <button type="button" class="primary" (click)="turnOn()" [disabled]="busy()">
              {{ busy() ? 'Asking…' : 'Turn on notifications' }}
            </button>
            <button type="button" (click)="notNow()">Not now</button>
          </div>
        </div>
      </section>
    }
  `,
  styleUrl: './notify-nudge.component.scss',
})
export class NotifyNudgeComponent {
  private readonly push = inject(PushService);
  private readonly auth = inject(AuthService);

  readonly busy = signal(false);
  private readonly hidden = signal(isSnoozed());

  readonly visible = computed(() => {
    if (this.hidden() || !this.push.native() || !this.auth.isAuthenticated()) return false;
    const state = this.push.permission();
    return state === 'prompt' || state === 'denied';
  });

  async turnOn(): Promise<void> {
    this.busy.set(true);
    try {
      await this.push.enable();
    } finally {
      this.busy.set(false);
    }
  }

  notNow(): void {
    try {
      const count = Number(localStorage.getItem(DISMISS_COUNT_KEY) ?? 0) + 1;
      localStorage.setItem(DISMISS_COUNT_KEY, String(count));
      localStorage.setItem(SNOOZE_KEY, String(count >= MAX_DISMISSALS ? Number.MAX_SAFE_INTEGER : Date.now() + SNOOZE_MS));
    } catch { /* storage unavailable: hidden for this visit only */ }
    this.hidden.set(true);
  }
}

function isSnoozed(): boolean {
  try {
    return Number(localStorage.getItem(SNOOZE_KEY) ?? 0) > Date.now();
  } catch {
    return false;
  }
}
