import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ThemeService } from '../../../core/theme.service';
import { SplashComponent } from '../../../shell/splash/splash.component';

/**
 * Landing (Figma node 4:2) — the app's front door and step one of onboarding.
 *
 * The promise on this screen is the product's whole claim: SIDDHA is a way of
 * life guide rooted in real calculation, not a fear-based prediction machine.
 * The footer names the sources and, deliberately, what the app will not do.
 *
 * The design's mocked status bar (9:41 and a battery) is a Figma artifact and
 * is not built: the real status bar belongs to the OS, and the shell already
 * reserves the safe area for it.
 */
@Component({
  selector: 'as-landing',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, SplashComponent],
  template: `
    <div class="landing-hero">
      <app-splash class="landing-mark" [dark]="theme.dark()" [markOnly]="true" aria-hidden="true" />
      <p class="wordmark">SIDDHA</p>
      <p class="eyebrow">YOUR WAY OF LIFE GUIDE</p>
      <h1 class="headline">Live with rhythm.<br />Move with clarity.</h1>
      <p class="lede">
        <span class="siddha-brand">SIDDHA</span> turns your daily timing, life
        patterns, and inner seasons into practical guidance for how to act,
        pause, reflect, and grow.
      </p>
    </div>

    <div class="actions">
      <a class="btn primary" [routerLink]="['/m', 'auth']" [queryParams]="{ mode: 'register' }">Begin your path</a>
      <a class="btn ghost" [routerLink]="['/m', 'auth']">I already walk with <span class="siddha-brand">SIDDHA</span></a>
      <p class="assurance">Classical wisdom · Daily practice · No fear, no fatalism</p>
    </div>
  `,
  styleUrl: './landing.component.scss',
  // Outside the shell, so the token host class must be applied here or every
  // var() silently falls back — see the build plan's first convention.
  host: { class: 'as-mobile' },
})
export class LandingComponent {
  protected readonly theme = inject(ThemeService);
}
