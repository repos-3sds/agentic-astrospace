import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DayGaugeComponent } from '../day-gauge/day-gauge.component';
import { DayQualitySheetComponent, DaySignal } from './day-quality-sheet.component';
import { ListenSheetComponent } from './listen-sheet.component';
import {
  EvidenceRow,
  WhyReadingSheetComponent,
} from '../why-reading/why-reading-sheet.component';
import { KundliStore } from '../../../core/kundli.store';
import { VedicService } from '../../../core/vedic.service';
import { DailyGuidancePayload } from '../../../core/models';
import { ProfileSwitcherComponent } from '../profile-switcher/profile-switcher.component';
import { PreferencesService } from '../../../core/preferences.service';
import { GenericErrorComponent } from '../states/generic-error.component';

/**
 * Turns the engine's day score into a gauge position.
 *
 * `_score_day` in astrospace/context/daily.py returns an **unbounded signed
 * integer** — tara contributes ±2, chandrabala −3…+1, and every supportive or
 * challenging rule shifts it further. Its meaningful output is the *band*
 * (supportive ≥3, positive ≥1, mixed ≥−1, else caution); the raw number is an
 * internal tally, not a percentage.
 *
 * Clamping it into 0–100, which is what this used to do, meant a real day
 * scoring −4 rendered as an empty ring reading 0, and even an excellent +5 day
 * rendered as 5. The gauge was near-empty for every genuine reading.
 *
 * So the score is mapped through its own band into that band's slice of the
 * dial. The number shown is a position on a four-band indicator, not a
 * percentage of anything — and because it is derived from the same threshold
 * that picks the label, the ring and the words can never disagree.
 */
export function gaugePositionFromScore(score: number): number {
  // [lower score bound, gauge floor, gauge ceiling] per band, mirroring the
  // thresholds in _score_day so the two stay in step.
  const bands: [number, number, number][] = [
    [3, 76, 100],   // supportive
    [1, 51, 75],    // positive
    [-1, 26, 50],   // mixed
    [-Infinity, 1, 25], // caution
  ];
  const [lower, floor, ceiling] = bands.find(([min]) => score >= min)!;
  // Spread the band across its slice, saturating four points beyond its start.
  const span = Number.isFinite(lower) ? 4 : 4;
  const within = Math.min(1, Math.max(0, (score - (Number.isFinite(lower) ? lower : -6)) / span));
  return Math.round(floor + within * (ceiling - floor));
}

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
    ProfileSwitcherComponent,
    GenericErrorComponent,
  ],
  templateUrl: './today.component.html',
  styleUrl: './today.component.scss',
})
export class TodayComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  protected readonly preferences = inject(PreferencesService);
  protected readonly whyMode = computed(() => ({
    guided: 'Guided view — the meaning first, with unfamiliar terms translated.',
    balanced: 'Balanced view — plain first, the calculation underneath.',
    practitioner: 'Practitioner view — exact factors, conventions, and evidence.',
  })[this.preferences.experienceMode()]);

  readonly loading = signal(true);
  readonly loadError = signal<string | null>(null);
  readonly emptyProfile = signal(false);
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
  readonly profileSwitcherOpen = signal(false);

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

  constructor() {
    void this.loadToday();
  }

  protected async loadToday(): Promise<void> {
    this.loading.set(true);
    this.loadError.set(null);
    this.emptyProfile.set(false);
    try {
      await this.kundlis.load();
      const profile = this.kundlis.active();
      if (!profile) {
        this.emptyProfile.set(true);
        return;
      }
      const daily = await this.vedic.dailyGuidance(profile.id);
      this.applyDaily(profile.name, profile.birth_city, daily);
    } catch (error) {
      this.loadError.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  private applyDaily(name: string, city: string, daily: DailyGuidancePayload): void {
    const band: DayBand = daily.verdict.tone === 'caution'
      ? 'tough'
      : daily.verdict.tone === 'mixed' ? 'mixed' : 'steady';
    const dateLabel = new Intl.DateTimeFormat('en', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      timeZone: 'UTC',
    }).format(new Date(`${daily.date}T00:00:00Z`));
    this.view.set({
      greetingName: name,
      initial: name.slice(0, 1).toUpperCase(),
      dateLabel,
      place: daily.provenance.place.city || city,
      score: gaugePositionFromScore(daily.verdict.score),
      band,
      scoreLabel: band === 'steady' ? 'Steady' : band === 'mixed' ? 'Mixed' : 'Take care',
      verdict: daily.verdict.headline,
      // reading.summary, not verdict.text. The card is designed for two lines
      // (~90 chars) and verdict.text runs to ~470 — it pushed the Listen button
      // down and shoved Do/Avoid off-screen entirely. The long form is not
      // lost: it is what the "Why this reading?" sheet opens with.
      detail: daily.reading.summary,
      doItem: daily.do_today[0]?.text ?? daily.reading.best_for[0] ?? daily.reading.focus,
      avoidItem: daily.avoid_today[0]?.text ?? daily.reading.avoid[0] ?? daily.reading.timing_note,
      nextWindowLabel: 'TIMING NOTE',
      nextWindowValue: daily.reading.timing_note,
      nextWindowIn: '',
    });
    this.signals.set([
      {
        name: 'Tarabala',
        verdict: daily.tarabala.favourable ? 'FAVOURABLE' : 'CAUTION',
        tone: daily.tarabala.favourable ? 'good' : 'warn',
        explanation: daily.tarabala.note ?? `${daily.tarabala.tara} tara for today.`,
      },
      {
        name: 'Chandrabala',
        verdict: daily.chandrabala.favourable ? 'STRONG' : 'CAUTION',
        tone: daily.chandrabala.favourable ? 'good' : 'warn',
        explanation: `Moon is ${daily.chandrabala.house_from_rashi} houses from your natal Moon.`,
      },
      ...daily.context.active_gochara.slice(0, 1).map((transit) => ({
        name: transit.planet,
        verdict: (transit.severity ?? 'ACTIVE').toUpperCase(),
        tone: transit.severity === 'high' ? 'warn' as const : 'good' as const,
        explanation: transit.name,
      })),
    ]);
    this.summary.set(daily.reading.summary);
    // The full narrative leads the evidence sheet, so nothing the engine wrote
    // is dropped — it just stops overflowing the card it was never sized for.
    this.plainWords.set([daily.verdict.text, ...daily.reading.plain_why]);
    this.calculation.set(daily.reading.technical_why.map((value, index) => ({
      label: `Signal ${index + 1}`,
      value,
    })));
    this.statSections.set([
      {
        eyebrow: 'TODAY’S SKY · PANCHANG',
        columns: 2,
        cells: [
          { label: 'TITHI', value: daily.star_of_day.tithi },
          { label: 'NAKSHATRA', value: daily.star_of_day.nakshatra },
          { label: 'VARA', value: daily.vara },
          { label: 'MOON SIGN', value: daily.star_of_day.moon_rashi },
        ],
      },
      {
        eyebrow: 'TODAY · CHANGES DAILY',
        columns: 3,
        cells: [
          { label: 'COLOUR', value: daily.color.name },
          { label: 'NUMBER', value: String(daily.number.value) },
          { label: 'TARABALA', value: daily.tarabala.favourable ? 'Good' : 'Caution' },
        ],
      },
      {
        eyebrow: 'ALWAYS · YOUR SIGNATURE',
        columns: 3,
        cells: [
          { label: 'LUCKY NO.', value: String(daily.lucky_numbers.astrological.number) },
          { label: 'GEM', value: daily.lucky_signature.gem },
          { label: 'DIRECTION', value: daily.lucky_signature.direction },
        ],
      },
    ]);
  }
}
