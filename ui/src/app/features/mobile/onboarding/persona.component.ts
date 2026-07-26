import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

/** How much depth a reader wants. Drives disclosure, never content. */
export type PersonaId = 'guided' | 'balanced' | 'practitioner';

/** How the app words things when the reading is unwelcome. */
export type ToneId = 'gentle' | 'direct';

interface PersonaOption {
  id: PersonaId;
  icon: string;
  title: string;
  badge: string;
  badgeTone: 'gold' | 'accent' | 'good';
  detail: string;
}

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
  imports: [RouterLink],
  template: `
    <div class="top">
      <header class="topbar">
        <a class="back" [routerLink]="['/m', 'disclaimers']" aria-label="Back">
          <img src="mobile/back.svg" alt="" aria-hidden="true" />
        </a>
        <p class="step">STEP 1 OF 2</p>
      </header>

      <h1 class="headline">How do you like<br />your answers?</h1>
      <p class="lede">This tailors how much depth you see. You can change it anytime.</p>

      <div class="options" role="radiogroup" aria-label="How much depth to show">
        @for (o of options; track o.id) {
          <button
            class="option"
            type="button"
            role="radio"
            [class.is-on]="o.id === persona()"
            [attr.aria-checked]="o.id === persona()"
            (click)="persona.set(o.id)"
          >
            <span class="option-icon">
              <img [src]="'mobile/' + o.icon + '.svg'" alt="" aria-hidden="true" />
            </span>
            <span class="option-text">
              <span class="option-head">
                <span class="option-title">{{ o.title }}</span>
                <span class="badge" [attr.data-tone]="o.badgeTone">{{ o.badge }}</span>
              </span>
              <span class="option-detail">{{ o.detail }}</span>
            </span>
            @if (o.id === persona()) {
              <span class="tick" aria-hidden="true">
                <img src="mobile/check.svg" alt="" />
              </span>
            } @else {
              <img class="radio" src="mobile/radio-off.svg" alt="" aria-hidden="true" />
            }
          </button>
        }
      </div>

      <p class="section">WHEN SOMETHING’S TOUGH</p>
      <!-- Wording only. A flag is a flag in both tones — see the class comment. -->
      <div class="tones" role="radiogroup" aria-label="Tone when a reading is tough">
        @for (t of tones; track t.id) {
          <button
            class="tone"
            type="button"
            role="radio"
            [class.is-on]="t.id === tone()"
            [attr.aria-checked]="t.id === tone()"
            (click)="tone.set(t.id)"
          >{{ t.label }}</button>
        }
      </div>
    </div>

    <a class="btn" [routerLink]="['/m', 'birth-details']">Continue</a>
  `,
  styleUrl: './persona.component.scss',
  // Outside the shell, so the token host class must be applied here or every
  // var() silently falls back — see the build plan's first convention.
  host: { class: 'as-mobile' },
})
export class PersonaComponent {
  readonly persona = signal<PersonaId>('balanced');
  readonly tone = signal<ToneId>('gentle');

  protected readonly options: PersonaOption[] = [
    {
      id: 'guided',
      icon: 'persona-guided',
      title: 'Guided',
      badge: 'SIMPLE',
      badgeTone: 'gold',
      detail: 'Just tell me, simply. Plain answers, no jargon.',
    },
    {
      id: 'balanced',
      icon: 'persona-balanced',
      title: 'Balanced',
      badge: 'RECOMMENDED',
      badgeTone: 'accent',
      detail: 'Tell me — and show me why, one tap away.',
    },
    {
      id: 'practitioner',
      icon: 'persona-practitioner',
      title: 'Practitioner',
      badge: 'ADVANCED',
      badgeTone: 'good',
      detail: 'Full detail — charts, dashas, and the tools.',
    },
  ];

  protected readonly tones: { id: ToneId; label: string }[] = [
    { id: 'gentle', label: 'Be gentle' },
    { id: 'direct', label: 'Be direct' },
  ];
}
