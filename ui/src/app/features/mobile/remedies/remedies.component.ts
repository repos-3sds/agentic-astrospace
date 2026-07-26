import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ManglikCancellationSheetComponent } from '../chart/manglik-cancellation-sheet.component';

/** What kind of thing in the chart a remedy answers to. */
export type RemedyTone = 'warn' | 'bad' | 'good';

/** One practice. `icon` names the kind of act, not the planet. */
export interface RemedyPractice {
  icon: 'chant' | 'offer' | 'wear' | 'rite';
  text: string;
}

export interface RemedyCard {
  id: string;
  title: string;
  tagLabel: string;
  tone: RemedyTone;
  /** Why this is being shown at all — the chart fact behind it. */
  rationale: string;
  practices: RemedyPractice[];
  ctaLabel: string;
  /**
   * Where the action goes when it is a route. Manglik opens its shared sheet.
   */
  ctaRoute?: string[];
}

/**
 * Remedies — "What to do" (Figma node 29:55).
 *
 * Titled the way the design titles it. "Remedies" implies something is wrong
 * and this will fix it; "What to do" is the same content without the premise.
 *
 * Two product constraints are load-bearing here and are enforced in the
 * template rather than the data:
 *
 * - Remedies are **traditional practice, never "pay to remove"**. Every card
 *   carries "Traditional practice · not a guarantee" above its action, printed
 *   by the template so no card object can omit it and no future card can be
 *   added without it.
 * - A dosha is **a flag, not a verdict** — never suppressed, never escalated.
 *   The Manglik card says the influence is mild, common, and has a traditional
 *   cancellation. That wording is the constraint, not filler: dropping "common"
 *   escalates it, and dropping the flag entirely suppresses it.
 *
 * The lede states the limit once for the whole screen, and the per-card line
 * repeats it at the point of action, because that is where someone decides.
 */
@Component({
  selector: 'as-remedies',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, ManglikCancellationSheetComponent],
  templateUrl: './remedies.component.html',
  styleUrl: './remedies.component.scss',
})
export class RemediesComponent {
  readonly cancellationOpen = signal(false);
  readonly cards = signal<RemedyCard[]>([
    {
      id: 'saturn',
      title: 'For Saturn’s friction at work',
      tagLabel: 'SATURN DASHA',
      tone: 'warn',
      rationale:
        'Your Saturn period is highlighting patience and steady effort through October.',
      practices: [
        {
          icon: 'chant',
          text: 'Chant “Om Sham Shanaishcharaya Namah” · 108 times, Saturdays',
        },
        { icon: 'offer', text: 'Offer sesame oil or donate black sesame on Saturdays' },
        { icon: 'wear', text: 'Wear or hold something blue-black on tough days' },
      ],
      ctaLabel: 'Start streak',
      ctaRoute: ['/m', 'remedies', 'mantra'],
    },
    {
      id: 'manglik',
      title: 'For a gentle Manglik flag',
      tagLabel: 'MARRIAGE · FLAG',
      tone: 'bad',
      rationale:
        'A mild Manglik influence shows in your chart — this is common and has a traditional cancellation.',
      practices: [
        {
          icon: 'rite',
          text: 'Kumbh Vivah / Peepal puja before matching — many families already do this',
        },
        { icon: 'chant', text: 'Hanuman Chalisa on Tuesdays' },
      ],
      ctaLabel: 'View cancellation',
    },
  ]);
}
