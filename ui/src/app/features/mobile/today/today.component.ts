import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DayGaugeComponent } from '../day-gauge/day-gauge.component';
import { DayQualitySheetComponent, DaySignal } from './day-quality-sheet.component';
import { ListenSheetComponent } from './listen-sheet.component';
import { EvidenceRow, WhyReadingSheetComponent } from './why-reading-sheet.component';

/** Verdict bands. Named, not numeric, so tone rules can key off them. */
export type DayBand = 'steady' | 'mixed' | 'tough';

/** One labelled fact in the panchang grids below the fold. */
export interface StatCell {
  label: string;
  value: string;
}

/**
 * A labelled block of stat cells.
 *
 * `columns` is carried in the data rather than derived from the cell count
 * because the design pairs panchang limbs two-per-row even though there are
 * four of them — a wrapped three-column grid would regroup them wrongly.
 */
export interface StatSection {
  eyebrow: string;
  columns: 2 | 3;
  cells: StatCell[];
}

export interface TodayView {
  greetingName: string;
  initial: string;
  dateLabel: string;
  place: string;
  score: number;
  band: DayBand;
  scoreLabel: string;
  verdict: string;
  detail: string;
  doItem: string;
  avoidItem: string;
  nextWindowLabel: string;
  nextWindowValue: string;
  nextWindowIn: string;
}

/**
 * Today — the app's home (Figma nodes 13:2 above the fold, 20:2 scrolled).
 *
 * C1 requires one viewport to carry a plain verdict, one thing to do, one to
 * avoid, and a day-quality indicator; everything deeper is a swipe away. The
 * order here follows the design exactly rather than being re-derived.
 *
 * 20:2 is the same screen scrolled, not a second one, so the stat grids and
 * ask-suggestions below live here rather than on a route of their own.
 *
 * The copy below is the design's placeholder content. Wiring to
 * /api/v1/panchanga/{id}/today is the next step; the view model is already
 * shaped for it so the template does not change when real data lands.
 */
@Component({
  selector: 'as-today',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    DayGaugeComponent,
    DayQualitySheetComponent,
    ListenSheetComponent,
    RouterLink,
    WhyReadingSheetComponent,
  ],
  templateUrl: './today.component.html',
  styleUrl: './today.component.scss',
})
export class TodayComponent {
  readonly view = signal<TodayView>({
    greetingName: 'Lakshmi',
    initial: 'L',
    dateLabel: 'Friday, 25 July',
    place: 'Vijayawada',
    score: 72,
    band: 'steady',
    scoreLabel: 'Steady',
    verdict: 'A steady, workable day',
    detail:
      'Good momentum for work and errands — keep big money calls for the afternoon.',
    doItem: 'Start the work you’ve been delaying.',
    avoidItem: 'Signing final papers before noon.',
    nextWindowLabel: 'NEXT WINDOW TO AVOID',
    nextWindowValue: 'Rahu Kalam · 4:30–6:00 PM',
    nextWindowIn: 'in 2h',
  });

  protected readonly greeting = computed(() => `Namaste, ${this.view().greetingName}`);

  /** Contributors behind the score — C2 requires these be nameable, not opaque. */
  readonly signals = signal<DaySignal[]>([
    {
      name: 'Tarabala',
      verdict: 'FAVOURABLE',
      tone: 'good',
      explanation: 'Your star-count from the Moon supports the day.',
    },
    {
      name: 'Chandrabala',
      verdict: 'STRONG',
      tone: 'good',
      explanation: 'The Moon is well-placed from your sign.',
    },
    {
      name: 'Saturn transit',
      verdict: 'MILD FRICTION',
      tone: 'warn',
      explanation: 'Passing your 10th house — go steady at work.',
    },
  ]);

  readonly summary = signal(
    'A steady, workable day — good for routine work, gentle on big commitments.',
  );

  /** Which sheet is showing, if any. One signal so two cannot stack. */
  readonly openSheet = signal<'quality' | 'why' | 'listen' | null>(null);

  /** Audio language, chosen in the Listen sheet — see 23:25. */
  readonly audioLanguage = signal('English');

  readonly plainWords = signal([
    'You’re in a supportive stretch for steady, everyday work.',
    'Money and legal commitments are better after midday.',
  ]);

  readonly calculation = signal<EvidenceRow[]>([
    { label: 'Active period', value: 'Venus – Saturn' },
    { label: 'Moon transiting', value: 'Hasta · 12th' },
    { label: 'Key gochara', value: 'Saturn on 10th' },
  ]);

  // Always shown. A reading whose conventions are hidden is not reproducible —
  // the same chart under a different ayanamsa is a different answer.
  readonly conventions = signal([
    'Lahiri', 'Whole-sign', 'Vijayawada', 'High confidence',
  ]);

  /**
   * Below the fold (20:2). Grouped by how often each fact changes, which is the
   * design's own grouping: the panchang limbs, what turns over daily, and what
   * is fixed by the natal chart. Readers who do not know the Sanskrit terms can
   * still tell which numbers are about them and which are about the day.
   *
   * The limbs are convention-dependent — a purnimanta reader sees a different
   * month name for the same tithi. The convention actually used is stated in
   * the "Why this reading?" sheet rather than being implied away here.
   */
  readonly statSections = signal<StatSection[]>([
    {
      eyebrow: 'TODAY’S SKY · PANCHANG',
      columns: 2,
      cells: [
        { label: 'TITHI', value: 'Dvitiya' },
        { label: 'NAKSHATRA', value: 'Hasta' },
        { label: 'YOGA', value: 'Shubha' },
        { label: 'KARANA', value: 'Bava' },
      ],
    },
    {
      eyebrow: 'TODAY · CHANGES DAILY',
      columns: 3,
      cells: [
        { label: 'COLOUR', value: 'Maroon' },
        { label: 'NUMBER', value: '6' },
        { label: 'TARABALA', value: 'Good' },
      ],
    },
    {
      eyebrow: 'ALWAYS · YOUR SIGNATURE',
      columns: 3,
      cells: [
        { label: 'LUCKY NO.', value: '5' },
        { label: 'GEM', value: 'Ruby' },
        { label: 'DIRECTION', value: 'East' },
      ],
    },
  ]);

  /** Openers for Ask, seeded from the day so the tab is not a blank prompt. */
  readonly askSuggestions = signal([
    'Is today good to start new work?',
    'Best time to travel this evening?',
  ]);
}
