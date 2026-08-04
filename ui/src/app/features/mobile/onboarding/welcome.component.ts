import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

/** One commitment made before any birth data is asked for. */
interface Promise_ {
  icon: string;
  title: string;
  detail: string;
}

/**
 * Welcome (Figma node 6:2) — step two of onboarding.
 *
 * The three promises come *before* the form, not after it. Birth date, time and
 * place is the most personal thing this app ever asks for, and the order here
 * says what will be done with it before asking rather than in a policy page
 * afterwards.
 *
 * "Skip for now" is real and stays. An app that will not let you look around
 * before handing over your birth time has already broken the second promise.
 */
@Component({
  selector: 'as-welcome',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <div class="top">
      <img class="orb" src="mobile/orb-sm.svg" alt="" aria-hidden="true" />
      <p class="greeting">నమస్తే · Namaste</p>
      <h1 class="headline">Welcome to<br /><span class="brand-name">SIDDHA</span></h1>
      <p class="lede">
        Let’s begin with your birth details so <span class="siddha-brand">SIDDHA</span>
        can understand your personal rhythm and guide your everyday choices with care.
      </p>

      <ul class="promises">
        @for (p of promises(); track p.title) {
          <li class="promise">
            <span class="promise-icon">
              <img [src]="'mobile/' + p.icon + '.svg'" alt="" aria-hidden="true" />
            </span>
            <span class="promise-text">
              <span class="promise-title">{{ p.title }}</span>
              <span class="promise-detail">{{ p.detail }}</span>
            </span>
          </li>
        }
      </ul>
    </div>

    <div class="actions">
      <a class="btn" [routerLink]="['/m', 'disclaimers']">Continue</a>
      <!-- Real, and it stays: see the class comment. -->
      <a class="skip" [routerLink]="['/m', 'today']">Skip for now</a>
    </div>
  `,
  styleUrl: './welcome.component.scss',
  // Outside the shell, so the token host class must be applied here or every
  // var() silently falls back — see the build plan's first convention.
  host: { class: 'as-mobile' },
})
export class WelcomeComponent {
  protected readonly promises = signal<Promise_[]>([
    {
      icon: 'promise-computed',
      title: 'Wisdom with a foundation',
      detail: 'Guidance is rooted in real calculations, then translated for life.',
    },
    {
      icon: 'promise-private',
      title: 'Your path stays yours',
      detail: 'Your birth details and reflections are treated with care.',
    },
    {
      icon: 'promise-language',
      title: 'Guidance you can live with',
      // Was 'English & Telugu' — the app is not translated, so that promised
      // something onboarding could not deliver on the very screen that asks
      // for trust.
      detail: 'Simple words today, read aloud if you like. More languages are on the way.',
    },
  ]);
}
