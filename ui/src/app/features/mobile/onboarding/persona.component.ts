import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import {
  PersonaOption,
  PersonaPickerComponent,
} from '../persona-picker/persona-picker.component';
import { PreferencesService } from '../../../core/preferences.service';

/**
 * Persona (Figma node 8:2) — step four of onboarding.
 *
 * This sets how much depth is shown, not what is true. A Guided reader and a
 * Practitioner reader get the same computation and the same flags; one sees the
 * sentence and the other sees Shadbala underneath it. Nothing is withheld from
 * the simpler setting that would change what it means — the "Why this reading?"
 * sheet is reachable from every mode.
 *
 * The tone toggle is the same idea applied to wording. "Be gentle" changes how
 * an unwelcome reading is phrased; it never softens the reading itself, and it
 * cannot suppress a dosha, because a flag is a flag in both tones.
 */
@Component({
  selector: 'as-persona',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PersonaPickerComponent, RouterLink],
  template: `
    <div class="top">
      <header class="topbar">
        <a class="back" [routerLink]="['/m', 'disclaimers']" aria-label="Back">
          <img src="mobile/back.svg" alt="" aria-hidden="true" />
        </a>
        <p class="step">SETUP 4 OF 6</p>
      </header>

      <h1 class="headline">How should <span class="siddha-brand">Siddha</span><br />walk with you?</h1>
      <p class="lede">Choose the depth of guidance you want. You can change it anytime.</p>

      <as-persona-picker
        [options]="options"
        [(persona)]="persona"
        [(tone)]="tone"
      />
    </div>

    <a class="btn" [routerLink]="['/m', 'customize']">Continue</a>
  `,
  styleUrl: './persona.component.scss',
  // Outside the shell, so the token host class must be applied here or every
  // var() silently falls back — see the build plan's first convention.
  host: { class: 'as-mobile' },
})
export class PersonaComponent {
  private readonly preferences = inject(PreferencesService);
  readonly persona = this.preferences.experienceMode;
  readonly tone = this.preferences.tone;

  readonly options: PersonaOption[] = [
    {
      id: 'guided',
      icon: 'persona-guided',
      title: 'Guided',
      badge: 'SIMPLE',
      badgeTone: 'gold',
      detail: 'Gentle daily guidance in plain words, with practice first.',
    },
    {
      id: 'balanced',
      icon: 'persona-balanced',
      title: 'Balanced',
      badge: 'RECOMMENDED',
      badgeTone: 'accent',
      detail: 'Clear guidance with the reasoning one tap away.',
    },
    {
      id: 'practitioner',
      icon: 'persona-practitioner',
      title: 'Practitioner',
      badge: 'ADVANCED',
      badgeTone: 'good',
      detail: 'Full depth for charts, dashas, transits, and study.',
    },
  ];
}
