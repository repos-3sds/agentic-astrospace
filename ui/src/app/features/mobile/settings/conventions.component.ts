import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

/** One selectable convention within a group. */
export interface ConventionChoice {
  id: string;
  label: string;
}

/** A group of mutually exclusive conventions. */
export interface ConventionGroup {
  key: 'ayanamsha' | 'nodes' | 'style';
  eyebrow: string;
  /** Glyph shape for the group — circle, dash, square, per the design. */
  glyph: 'circle' | 'dash' | 'square';
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
  imports: [RouterLink],
  templateUrl: './conventions.component.html',
  styleUrl: './conventions.component.scss',
})
export class ConventionsComponent {
  readonly groups: ConventionGroup[] = [
    {
      key: 'ayanamsha',
      eyebrow: 'AYANAMSHA',
      glyph: 'circle',
      choices: [
        { id: 'lahiri', label: 'Lahiri' },
        { id: 'raman', label: 'Raman' },
        { id: 'kp', label: 'KP' },
      ],
    },
    {
      key: 'nodes',
      eyebrow: 'NODE TYPE',
      glyph: 'dash',
      choices: [
        { id: 'mean', label: 'Mean' },
        { id: 'true', label: 'True' },
      ],
    },
    {
      key: 'style',
      eyebrow: 'CHART STYLE',
      glyph: 'square',
      choices: [
        { id: 'eastern', label: 'Eastern' },
        { id: 'south', label: 'South Indian' },
        { id: 'north', label: 'North Indian' },
      ],
    },
  ];

  /** Current selection per group. Defaults match what provenance reports. */
  readonly selected = signal<Record<ConventionGroup['key'], string>>({
    ayanamsha: 'lahiri',
    nodes: 'mean',
    style: 'eastern',
  });

  protected choose(key: ConventionGroup['key'], id: string): void {
    this.selected.update((current) => ({ ...current, [key]: id }));
  }
}
