import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { SplashComponent } from '../../../shell/splash/splash.component';

interface PromiseRow {
  icon: string;
  title: string;
  detail: string;
}

/**
 * Welcome — step two of onboarding.
 *
 * This screen uses the same native animated Siddha mark as the splash and
 * get-started screen. It avoids a generic carousel because this is still the
 * first-run promise, not a feature tour.
 */
@Component({
  selector: 'as-welcome',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, SplashComponent],
  templateUrl: './welcome.component.html',
  styleUrl: './welcome.component.scss',
  // Outside the shell, so the token host class must be applied here or every
  // var() silently falls back — see the build plan's first convention.
  host: { class: 'as-mobile' },
})
export class WelcomeComponent {
  protected readonly promises = signal<PromiseRow[]>([
    {
      icon: 'promise-computed',
      title: 'Daily guidance, not generic horoscope copy',
      detail: 'Your timing comes from panchanga, dashas, transits, and your active profile.',
    },
    {
      icon: 'figma-yantra-book-open',
      title: 'Plain meaning first',
      detail: 'Guided, Balanced, and Practitioner modes change depth without changing the truth.',
    },
    {
      icon: 'promise-private',
      title: 'No fear, no fatalism',
      detail: 'Difficult signals are explained as choices and boundaries, never as verdicts.',
    },
  ]);
}
