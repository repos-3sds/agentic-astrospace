import { ChangeDetectionStrategy, Component, inject, input, model } from '@angular/core';
import { HapticsService } from '../../../core/haptics.service';

/** How much depth a reader wants. Drives disclosure, never content. */
export type PersonaId = 'guided' | 'balanced' | 'practitioner';

/** How the app words things when the reading is unwelcome. */
export type ToneId = 'gentle' | 'direct';

export interface PersonaOption {
  id: PersonaId;
  icon: string;
  title: string;
  badge: string;
  badgeTone: 'gold' | 'accent' | 'good';
  detail: string;
}

/**
 * The persona and tone picker, shared by onboarding (8:2) and Settings (67:89).
 *
 * The same control in two places: onboarding badges the default RECOMMENDED,
 * Settings badges it CURRENT. That is the only difference, so it is a badge
 * string rather than two components — the alternative is two copies of the
 * selected-state styling drifting apart, which is how a "recommended" option
 * ends up looking unselected on one of the two screens.
 *
 * What this control does *not* do is the important part. Persona sets how much
 * depth is shown, not what is true: Guided and Practitioner get the same
 * computation and the same flags. Tone changes wording only. Neither can
 * suppress a dosha, and neither changes the refer-out boundary — the Settings
 * screen says so in as many words.
 */
@Component({
  selector: 'as-persona-picker',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="options" role="radiogroup" aria-label="How much depth to show">
      @for (o of options(); track o.id) {
        <button
          class="option"
          type="button"
          role="radio"
          [class.is-on]="o.id === persona()"
          [attr.aria-checked]="o.id === persona()"
          (click)="choosePersona(o.id)"
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
          (click)="chooseTone(t.id)"
        >{{ t.label }}</button>
      }
    </div>
  `,
  styleUrl: './persona-picker.component.scss',
})
export class PersonaPickerComponent {
  /** Two-way, so either host owns the value without re-plumbing events. */
  readonly persona = model<PersonaId>('balanced');
  readonly tone = model<ToneId>('gentle');

  /** Badge text differs by host — RECOMMENDED in onboarding, CURRENT in settings. */
  readonly options = input.required<PersonaOption[]>();

  protected readonly tones: { id: ToneId; label: string }[] = [
    { id: 'gentle', label: 'Be gentle' },
    { id: 'direct', label: 'Be direct' },
  ];

  private readonly haptics = inject(HapticsService);

  // Only buzz when the value actually changes. Re-tapping the selected option
  // is a no-op, and a confirmation for "nothing happened" teaches the reader
  // that the feedback means nothing.
  protected choosePersona(id: PersonaId): void {
    if (id === this.persona()) return;
    this.persona.set(id);
    this.haptics.select();
  }

  protected chooseTone(id: ToneId): void {
    if (id === this.tone()) return;
    this.tone.set(id);
    this.haptics.select();
  }
}
