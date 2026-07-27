import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import {
  PersonaOption,
  PersonaPickerComponent,
} from '../persona-picker/persona-picker.component';
import { PreferencesService } from '../../../core/preferences.service';

/**
 * Settings — Mode & tone (Figma node 67:89).
 *
 * The same control onboarding uses, badged CURRENT instead of RECOMMENDED,
 * because here it reports a state rather than suggesting one.
 *
 * The footnote is the screen's real content: health, legal and money questions
 * refer out to a professional no matter what is selected here. Someone who
 * picks Practitioner and Be direct might reasonably assume they have opted into
 * blunter answers on everything — this says plainly that the boundary is not a
 * preference, so nobody discovers it by hitting it.
 */
@Component({
  selector: 'as-settings-mode-tone',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PersonaPickerComponent, RouterLink],
  templateUrl: './mode-tone.component.html',
  styleUrl: './mode-tone.component.scss',
})
export class ModeToneComponent {
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
      detail: 'Just tell me, simply. Plain answers, no jargon.',
    },
    {
      id: 'balanced',
      icon: 'persona-balanced',
      title: 'Balanced',
      badge: 'CURRENT',
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
}
