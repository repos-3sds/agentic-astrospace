import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { PreferencesService } from '../../../core/preferences.service';

/** One of the app's standing limits, and the tone it is stated in. */
interface Vow {
  icon: string;
  tone: 'accent' | 'gold' | 'good';
  title: string;
  detail: string;
}

/**
 * "Our promise to you" — the first thing a new reader is asked, before the
 * account exists (Hawk, 2026-10-30: consents "in the beginning itself").
 *
 * The promises are not legal boilerplate. Each line is a constraint enforced
 * elsewhere in the code:
 *
 * - "Signals, not fate" — a dosha is never suppressed and never escalated;
 *   see the Manglik card on the remedies list.
 * - "Some questions need a professional" — medical, legal and financial
 *   intents refer out instead of being answered; see the refer-out screen.
 * - "No fear, ever" — no death or lifespan prediction, and no remedy sold as
 *   a fix; see the mantra tracker's caveat.
 *
 * Then the reader's choices, each stated on its own. Readings written by the
 * Siddha Agents is the one the app needs, so it is what the button agrees to
 * (App Review 5.1.2(i): explicit, before chart data reaches an AI service).
 * The app names no AI company (Hawk, 2026-10-30); the Privacy Policy does.
 * Usage reports start off and stay off unless switched on. Daily email is
 * asked later, on the first insight, next to the morning notification.
 */
@Component({
  selector: 'as-disclaimers',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackLinkDirective, RouterLink],
  template: `
    <header class="topbar">
      <a class="back" [asBack]="['/m', 'start']" aria-label="Back">
        <img src="mobile/back.svg" alt="" aria-hidden="true" />
      </a>
    </header>

    <div class="top">
      <p class="eyebrow">BEFORE YOU BEGIN</p>
      <h1 class="headline">Our promise to you</h1>

      <ul class="vows">
        @for (v of vows; track v.title) {
          <li class="vow">
            <span class="vow-icon" [attr.data-tone]="v.tone">
              <img [src]="'mobile/' + v.icon + '.svg'" alt="" aria-hidden="true" />
            </span>
            <span class="vow-text">
              <span class="vow-title">{{ v.title }}</span>
              <span class="vow-detail">{{ v.detail }}</span>
            </span>
          </li>
        }
      </ul>

      <section class="choices" aria-labelledby="choices-title">
        <p class="eyebrow" id="choices-title">YOUR CHOICES</p>
        <div class="choice">
          <span class="vow-text">
            <span class="vow-title">Readings are written by our Siddha Agents</span>
            <span class="vow-detail">They use your chart and your question. Never your email address.</span>
          </span>
        </div>
        <div class="choice">
          <span class="vow-text">
            <span class="vow-title" id="usage-title">Share usage and crash reports</span>
            <span class="vow-detail">Anonymous. Helps us find and fix problems.</span>
          </span>
          <button
            class="switch"
            type="button"
            role="switch"
            [class.is-on]="shareUsage()"
            [attr.aria-checked]="shareUsage()"
            aria-labelledby="usage-title"
            (click)="shareUsage.set(!shareUsage())"
          ></button>
        </div>
      </section>
    </div>

    <div class="actions">
      <a class="btn" [routerLink]="next" [queryParams]="nextParams" (click)="recordConsent()">Agree and continue</a>
      <p class="note">You can change these any time in Settings.</p>
    </div>
  `,
  styleUrl: './disclaimers.component.scss',
  // Outside the shell, so the token host class must be applied here or every
  // var() silently falls back — see the build plan's first convention.
  host: { class: 'as-mobile' },
})
export class DisclaimersComponent {
  private readonly preferences = inject(PreferencesService);
  /**
   * From the intro (?then=register) this leads to sign-up. A reader who
   * signed in without seeing it (Google from the Sign in tab, a magic link)
   * is sent here by the birth details guard and carries on with setup.
   */
  protected readonly beforeAccount = inject(ActivatedRoute).snapshot.queryParamMap.get('then') === 'register';
  protected readonly next = this.beforeAccount ? ['/m', 'auth'] : ['/m', 'birth-details'];
  protected readonly nextParams = this.beforeAccount ? { mode: 'register' } : null;
  protected readonly shareUsage = signal(this.preferences.usageAsked() && this.preferences.shareUsage());

  protected recordConsent(): void {
    this.preferences.shareUsage.set(this.shareUsage());
    this.preferences.usageAsked.set(true);
    // "Agree and continue" agrees to the first choice: readings written by
    // the Siddha Agents (App Review 5.1.2(i)).
    this.preferences.aiSharingAgreed.set(true);
  }

  protected readonly vows: Vow[] = [
    {
      icon: 'vow-flag',
      tone: 'accent',
      title: 'Signals, not fate',
      detail: 'Patterns to reflect on, never fixed outcomes.',
    },
    {
      icon: 'vow-scope',
      tone: 'gold',
      title: 'Some questions need a professional',
      detail: 'For health, legal or money decisions we point you to an expert.',
    },
    {
      icon: 'vow-nofear',
      tone: 'good',
      title: 'No fear, ever',
      detail: 'No death or lifespan predictions, and nothing to pay to "remove".',
    },
  ];
}
