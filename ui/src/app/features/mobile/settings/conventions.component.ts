import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import {
  DefaultAyanamsha,
  DefaultChartStyle,
  DefaultNodeType,
  PreferencesService,
} from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { SelectHapticDirective } from '../shared/select-haptic.directive';
import { StickyBarDirective } from '../shared/sticky-bar.directive';

/** One selectable convention within a group. */
export interface ConventionChoice {
  id: string;
  label: string;
  /** One plain line on who uses it, so the choice is recognisable. */
  detail: string;
  isDefault?: boolean;
}

/** A group of mutually exclusive conventions. */
export interface ConventionGroup {
  key: 'ayanamsha' | 'nodes' | 'style';
  eyebrow: string;
  /** What the group changes, in plain words. */
  note: string;
  choices: ConventionChoice[];
}

/**
 * Settings — Conventions (Figma node 69:117).
 *
 * The most consequential screen in Settings, and the one the provenance sheet
 * links to. Ayanamsha and node type are genuinely disputed in the tradition:
 * two competent astrologers using Lahiri and Raman disagree about the same
 * birth, and neither is wrong. Changing anything here changes every reading in
 * the app.
 *
 * That is why the lede says "change to match your practice" rather than
 * offering a recommendation. The app has a default, states it in provenance,
 * and does not pretend the alternatives are errors.
 *
 * Chart style is different in kind — Eastern, South and North draw the same
 * computed chart three ways, so it changes nothing but recognition. It sits
 * here anyway because to a reader both are "how my chart is set up".
 */
@Component({
  selector: 'as-settings-conventions',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [StickyBarDirective, BackLinkDirective, SelectHapticDirective],
  templateUrl: './conventions.component.html',
  styleUrl: './conventions.component.scss',
})
export class ConventionsComponent {
  protected readonly preferences = inject(PreferencesService);
  private readonly vedic = inject(VedicService);

  /**
   * Every group is a pick-one, so every row is the same round radio (U30:
   * the design's circle, dash and square glyphs read as three different
   * kinds of control, and the square looked like a multi-select).
   */
  readonly groups: ConventionGroup[] = [
    {
      key: 'ayanamsha',
      eyebrow: 'AYANAMSHA',
      note: 'Where the zodiac starts. Changes planet degrees a little, and sometimes a sign.',
      choices: [
        { id: 'lahiri', label: 'Lahiri', detail: 'Used by most Indian panchangams and the Government of India.', isDefault: true },
        { id: 'raman', label: 'Raman', detail: 'From B. V. Raman’s books. Differs from Lahiri by about 1½°.' },
        { id: 'krishnamurti', label: 'KP', detail: 'Krishnamurti Paddhati, for KP astrologers.' },
      ],
    },
    {
      key: 'nodes',
      eyebrow: 'RAHU AND KETU',
      note: 'How Rahu and Ketu are placed. The two differ by under 2°.',
      choices: [
        { id: 'mean', label: 'Mean', detail: 'The smooth average position. Used by most panchangams.', isDefault: true },
        { id: 'true', label: 'True', detail: 'The exact position on the day, with its small wobble.' },
      ],
    },
    {
      key: 'style',
      eyebrow: 'CHART DRAWING',
      note: 'Only how the chart is drawn. The planets stay the same.',
      choices: [
        { id: 'south', label: 'South Indian', detail: 'Signs fixed in a square. Common in the South.', isDefault: true },
        { id: 'north', label: 'North Indian', detail: 'Houses fixed in a diamond. Common in the North.' },
        { id: 'eastern', label: 'Eastern', detail: 'Used in Bengal, Odisha and Assam.' },
      ],
    },
  ];

  protected choose(key: ConventionGroup['key'], id: string): void {
    if (key === 'ayanamsha' && this.isAyanamsha(id)) {
      this.preferences.ayanamsha.set(id);
      this.vedic.invalidateAll();
      return;
    }
    if (key === 'nodes' && this.isNodeType(id)) {
      this.preferences.nodeType.set(id);
      this.vedic.invalidateAll();
      return;
    }
    if (key === 'style' && this.isChartStyle(id)) {
      this.preferences.chartStyle.set(id);
    }
  }

  protected selected(key: ConventionGroup['key']): string {
    if (key === 'ayanamsha') return this.preferences.ayanamsha();
    if (key === 'nodes') return this.preferences.nodeType();
    return this.preferences.chartStyle();
  }

  private isAyanamsha(value: string): value is DefaultAyanamsha {
    return value === 'lahiri' || value === 'raman' || value === 'krishnamurti';
  }

  private isNodeType(value: string): value is DefaultNodeType {
    return value === 'mean' || value === 'true';
  }

  private isChartStyle(value: string): value is DefaultChartStyle {
    return value === 'eastern' || value === 'south' || value === 'north';
  }
}
