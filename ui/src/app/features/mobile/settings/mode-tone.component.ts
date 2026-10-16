import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { Router } from '@angular/router';
import { PlanGateService } from '../../../core/plan-gate.service';
import {
  PersonaOption,
  PersonaPickerComponent,
} from '../persona-picker/persona-picker.component';
import { PreferencesService } from '../../../core/preferences.service';
import { BackLinkDirective } from '../../../core/back-link.directive';

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
  imports: [BackLinkDirective, PersonaPickerComponent],
  templateUrl: './mode-tone.component.html',
  styleUrl: './mode-tone.component.scss',
})
export class ModeToneComponent {
  private readonly preferences = inject(PreferencesService);
  private readonly gate = inject(PlanGateService);
  private readonly router = inject(Router);
  readonly persona = this.preferences.experienceMode;
  readonly tone = this.preferences.tone;

  /** Practitioner mode comes with the Practitioner plan; without it, Plans opens instead. */
  protected choose(id: PersonaOption['id']): void {
    if (id === 'practitioner' && !this.gate.allows('practitioner.workflow')) {
      void this.router.navigate(['/m', 'subscription'], { queryParams: { from: 'practitioner.workflow', plan: 'practitioner' } });
      return;
    }
    this.persona.set(id);
  }

  readonly options = computed<PersonaOption[]>(() => [
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
      badge: 'CURRENT',
      badgeTone: 'accent',
      detail: 'Clear guidance with the reasoning one tap away.',
    },
    {
      id: 'practitioner',
      icon: 'persona-practitioner',
      title: 'Practitioner',
      badge: this.gate.allows('practitioner.workflow') ? 'ADVANCED' : 'PLAN',
      badgeTone: 'good',
      detail: 'Full depth for charts, dashas, transits, and study.',
    },
  ]);
}
