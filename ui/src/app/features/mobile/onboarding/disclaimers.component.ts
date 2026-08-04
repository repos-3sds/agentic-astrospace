import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

/** One of the app's standing limits, and the tone it is stated in. */
interface Vow {
  icon: string;
  tone: 'accent' | 'gold' | 'good';
  title: string;
  detail: string;
}

/**
 * Disclaimers (Figma node 7:2) — step three of onboarding, and the screen the
 * product's non-negotiables are actually stated on.
 *
 * These are not legal boilerplate. Each line is a constraint enforced elsewhere
 * in the code, and this screen is where the app says so before the reader has
 * given it anything:
 *
 * - "A flag, not a fate" — a dosha is never suppressed and never escalated;
 *   see the Manglik card on the remedies list.
 * - "Not medical, legal or financial advice" — those intents refer out instead
 *   of being answered; see the refer-out screen (27:83).
 * - "No fear, ever" — no death or lifespan prediction, and no remedy sold as a
 *   fix; see the mantra tracker's caveat.
 *
 * The button says "I understand — continue" rather than "Accept", because
 * nothing here is a term being agreed to. It is a description of behaviour.
 */
@Component({
  selector: 'as-disclaimers',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <header class="topbar">
      <a class="back" [routerLink]="['/m', 'welcome']" aria-label="Back">
        <img src="mobile/back.svg" alt="" aria-hidden="true" />
      </a>
      <a class="skip" [routerLink]="['/m', 'persona']">Skip</a>
    </header>

    <div class="top">
      <div class="art">
        <span class="art-disc">
          <img src="mobile/shield-hero.svg" alt="" aria-hidden="true" />
        </span>
      </div>

      <p class="eyebrow">BEFORE WE BEGIN</p>
      <h1 class="headline">A guide for choice, not a verdict</h1>

      <ul class="vows">
        @for (v of vows(); track v.title) {
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
    </div>

    <div class="actions">
      <div class="dots" aria-hidden="true">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot is-on"></span>
      </div>
      <a class="btn" [routerLink]="['/m', 'persona']">I understand — continue</a>
    </div>
  `,
  styleUrl: './disclaimers.component.scss',
  // Outside the shell, so the token host class must be applied here or every
  // var() silently falls back — see the build plan's first convention.
  host: { class: 'as-mobile' },
})
export class DisclaimersComponent {
  protected readonly vows = signal<Vow[]>([
    {
      icon: 'vow-flag',
      tone: 'accent',
      title: 'Signals, not fate',
      detail: 'We surface patterns for reflection, never fixed outcomes.',
    },
    {
      icon: 'vow-scope',
      tone: 'gold',
      title: 'Life guidance has boundaries',
      detail: 'For medical, legal, or financial concerns we point you to a professional.',
    },
    {
      icon: 'vow-nofear',
      tone: 'good',
      title: 'No fear, ever',
      detail: 'We never predict death or lifespan, and never sell fear as a fix.',
    },
  ]);
}
