import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

/**
 * Landing (Figma node 4:2) — the app's front door and step one of onboarding.
 *
 * The promise on this screen is the product's whole claim: every reading comes
 * from a real, auditable calculation rather than a generic horoscope. The
 * footer names the sources and, deliberately, what the app will not do — "no
 * fear, no upsell" is a commitment the rest of the app has to keep, which is
 * why the refer-out and remedy screens read the way they do.
 *
 * The design's mocked status bar (9:41 and a battery) is a Figma artifact and
 * is not built: the real status bar belongs to the OS, and the shell already
 * reserves the safe area for it.
 */
@Component({
  selector: 'as-landing',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <div class="landing-hero">
      <img class="orb" src="mobile/orb.svg" alt="" aria-hidden="true" />
      <p class="wordmark">ASTROSPACE</p>
      <p class="eyebrow">VEDIC ASTROLOGY, COMPUTED</p>
      <h1 class="headline">Understand your chart.<br />Know your timing.</h1>
      <p class="lede">
        Every reading is derived from a real, auditable calculation — not a
        generic horoscope.
      </p>
    </div>

    <div class="actions">
      <a class="btn primary" [routerLink]="['/m', 'welcome']">Get started</a>
      <!-- Sign-in (5:2) is not built yet, so this stays inert rather than
           routing somewhere that is not the sign-in screen. -->
      <button class="btn ghost" type="button">I already have a space</button>
      <p class="assurance">Swiss Ephemeris · Classical rules · No fear, no upsell</p>
    </div>
  `,
  styleUrl: './landing.component.scss',
  // Outside the shell, so the token host class must be applied here or every
  // var() silently falls back — see the build plan's first convention.
  host: { class: 'as-mobile' },
})
export class LandingComponent {}
