import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DayGaugeComponent } from '../day-gauge/day-gauge.component';
import { DayQualitySheetComponent, DaySignal } from './day-quality-sheet.component';
import { ListenSheetComponent } from './listen-sheet.component';
import {
  DoAvoidExplainer,
  EvidenceRow,
  SourceReference,
  WhyReadingSheetComponent,
} from '../why-reading/why-reading-sheet.component';
import { KundliStore } from '../../../core/kundli.store';
import { BirthDetailsCardComponent } from '../chart/birth-details-card.component';
import { VedicService } from '../../../core/vedic.service';
import { DailyGuidancePayload, VedicAll } from '../../../core/models';
import { FestivalService } from '../../../core/festival.service';
import { ProfileSwitcherComponent } from '../profile-switcher/profile-switcher.component';
import { PreferencesService } from '../../../core/preferences.service';
import { HapticsService } from '../../../core/haptics.service';
import { GenericErrorComponent } from '../states/generic-error.component';
import { AudioReadingSection, buildTodayAudioScript } from './audio-reading-script';
import {
  MobileSymbol,
  colorSymbol,
  directionSymbol,
  gemSymbol,
  nakshatraSymbol,
  tithiSymbol,
} from '../symbols/mobile-symbols';

/** Figma 212:751's dasha-chain chips ("Moon Mahā › Rahu Antar › Jup Prat › Ven Sookshma"). */
const DASHA_LEVEL_SHORT: Record<string, string> = {
  mahadasha: 'Mahā',
  antardasha: 'Antar',
  pratyantardasha: 'Prat',
  sookshmadasha: 'Sookshma',
};

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

function scoreReason(daily: DailyGuidancePayload): string {
  const highTransits = daily.context.active_gochara.filter((row) => row.severity === 'high').length;
  const difficultWindows = daily.muhurta_windows.filter((row) => row.kind === 'inauspicious').length;
  const supportiveWindows = daily.muhurta_windows.filter((row) => row.kind === 'auspicious').length;
  if (!daily.chandrabala.favourable) {
    return highTransits || difficultWindows
      ? 'The score is cautious mainly because your Moon support is weaker today, and one or more timing signals asks you to slow down.'
      : 'The score is cautious mainly because the Moon is not giving you its usual emotional steadiness today. Keep the day simple and avoid reactive decisions.';
  }
  if (!daily.tarabala.favourable) {
    return 'The score is mixed mainly because the day’s star is not fully aligned with you. It is usable, but better for steady follow-through than risky starts.';
  }
  if (highTransits) {
    return 'The score is moderated by an active transit pressure. Your base support is present, but patience matters around the area being stirred.';
  }
  if (supportiveWindows > difficultWindows) {
    return 'The score is supported by your Moon strength and helpful daily windows, so ordinary work and meaningful conversations get a cleaner rhythm.';
  }
  return 'The score is steady because your personal bala is supportive. Use the day with discipline rather than trying to force everything at once.';
}

function plainChandrabala(daily: DailyGuidancePayload): string {
  if (daily.chandrabala.chandrashtama) {
    return 'The Moon is in a sensitive position from your birth Moon, so reactions can feel sharper than usual.';
  }
  return daily.chandrabala.favourable
    ? 'The Moon is supporting your emotional steadiness today, so routine decisions should feel easier to hold.'
    : 'The Moon is not especially supportive today, so pause before reacting and leave space around important conversations.';
}

function plainTarabala(daily: DailyGuidancePayload): string {
  return daily.tarabala.favourable
    ? 'Today’s star has a helpful rhythm for you, so starting or completing ordinary work gets a little more support.'
    : 'Today’s star asks for care, so simplify plans and avoid forcing outcomes that can wait.';
}

function minutesSinceMidnight(hhmm: string): number {
  const [h, m] = hhmm.split(':').map(Number);
  return h * 60 + m;
}

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

/**
 * "Starts in 40m" / "Ends in 1h 10m" for the Rahu Kalam window the Timing
 * Note already names. Both "now" and the window are wall-clock times in the
 * same place timezone, so this is a same-timezone comparison, not a UTC
 * conversion — Intl.DateTimeFormat just reads today's wall clock in that
 * timezone rather than the device's own.
 */
function muhurtaCountdown(daily: DailyGuidancePayload): string {
  const rahu = daily.muhurta_windows.find((w) => w.name.startsWith('Rahu Kalam'));
  if (!rahu) return '';
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: daily.provenance.place.timezone,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).formatToParts(new Date());
  const part = (type: string) => parts.find((p) => p.type === type)?.value ?? '';
  // The guidance is cached per day; only show a live countdown for the day
  // it actually describes, not a stale "starts in" on yesterday's cache.
  if (`${part('year')}-${part('month')}-${part('day')}` !== daily.date) return '';
  const nowMinutes = Number(part('hour')) * 60 + Number(part('minute'));
  const [start, end] = rahu.time.split(/[–-]/).map(minutesSinceMidnight);
  if (nowMinutes < start) return `Starts in ${formatDuration(start - nowMinutes)}`;
  if (nowMinutes < end) return `Ends in ${formatDuration(end - nowMinutes)}`;
  return '';
}

/** Verdict bands. Named, not numeric, so tone rules can key off them. */
export type DayBand = 'steady' | 'mixed' | 'tough';

/** One labelled fact in the panchang grids below the fold. */
export interface StatCell {
  label: string;
  value: string;
  symbol?: MobileSymbol;
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
  doItems: string[];
  avoidItems: string[];
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
 * The view model starts empty on purpose. Rendering placeholder astrology as if
 * it were personalized is worse than a blank state; real cards appear only
 * after the daily-guidance payload or an in-memory cached payload is applied.
 */
@Component({
  selector: 'as-today',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    BirthDetailsCardComponent,
    DayGaugeComponent,
    DayQualitySheetComponent,
    ListenSheetComponent,
    RouterLink,
    WhyReadingSheetComponent,
    ProfileSwitcherComponent,
    GenericErrorComponent,
  ],
  host: {
    '[attr.data-band]': 'view()?.band || "steady"',
  },
  templateUrl: './today.component.html',
  styleUrl: './today.component.scss',
})
export class TodayComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  private readonly festivals = inject(FestivalService);
  private readonly route = inject(ActivatedRoute);
  protected readonly preferences = inject(PreferencesService);
  private readonly haptics = inject(HapticsService);
  private requestId = 0;
  protected readonly whyMode = computed(() => ({
    guided: 'Guided view - the life guidance first, with unfamiliar terms translated.',
    balanced: 'Balanced view - guidance first, the calculation underneath.',
    practitioner: 'Practitioner view - exact factors, conventions, and evidence.',
  })[this.preferences.experienceMode()]);

  readonly loading = signal(true);
  readonly loadError = signal<string | null>(null);
  readonly emptyProfile = signal(false);
  readonly view = signal<TodayView | null>(null);

  protected readonly headerInitial = computed(
    () => this.view()?.initial ?? this.kundlis.active()?.name.slice(0, 1).toUpperCase() ?? 'A',
  );
  protected readonly headerName = computed(
    () => this.view()?.greetingName ?? this.kundlis.active()?.name ?? 'there',
  );
  /** The profile's real name, or null. `headerName` falls back to "there",
   * which is a greeting and not a name — wrong for a details header. */
  protected readonly activeName = computed(() => this.kundlis.active()?.name ?? null);

  protected readonly headerDate = computed(() => this.view()?.dateLabel ?? 'Today');
  protected readonly greeting = computed(() => `Namaste, ${this.headerName()}`);
  protected readonly listenScript = computed(() =>
    this.audioSections().map((section) => section.text).join(' '),
  );
  private readonly loadedDaily = signal<{
    name: string;
    city: string;
    dateLabel: string;
    daily: DailyGuidancePayload;
  } | null>(null);
  protected readonly audioSections = computed<AudioReadingSection[]>(() => {
    const loaded = this.loadedDaily();
    if (!loaded) return [];
    return buildTodayAudioScript({
      ...loaded,
      experienceMode: this.preferences.experienceMode(),
      tone: this.preferences.tone(),
    });
  });

  /** Contributors behind the score — C2 requires these be nameable, not opaque. */
  readonly signals = signal<DaySignal[]>([]);

  readonly summary = signal('');
  readonly scoreReason = signal('');

  /** Which sheet is showing, if any. One signal so two cannot stack. */
  readonly openSheet = signal<'quality' | 'why' | 'listen' | null>(null);
  /** Birth constants for the header strip. Populated from the chart cache that
   * `prefetchChart()` already warms, so this costs no extra request. */
  readonly natal = signal<VedicAll | null>(null);

  readonly profileSwitcherOpen = signal(false);
  readonly detailsOpen = signal(false);

  /**
   * Open a sheet with a confirming tap.
   *
   * Only on the way *in*. Dismissal already has three affordances (scrim,
   * Escape, the sheet's own button) and buzzing on each would make closing
   * something feel like a consequence.
   */
  protected showSheet(kind: 'quality' | 'why' | 'listen'): void {
    this.haptics.tap();
    this.openSheet.set(kind);
  }

  /** Audio language, chosen in the Listen sheet — see 23:25. */
  readonly audioLanguage = signal('English');

  readonly plainWords = signal<string[]>([]);

  readonly calculation = signal<EvidenceRow[]>([]);

  /** Real KB citations behind today's routing — see context.references. */
  readonly references = signal<SourceReference[]>([]);

  /** Full reasoning behind each Do/Avoid card headline — see do_today/avoid_today. */
  readonly doAvoidExplained = signal<DoAvoidExplainer[]>([]);

  /**
   * Practitioner Board (Figma 212:751) — the dedicated dense dashboard for
   * practitioner mode, distinct from the Guided/Balanced Today layout rather
   * than a relabeled version of it.
   */
  protected readonly dashaChain = signal<{ level: string; lord: string; short: string }[]>([]);
  protected readonly panchangaDetails = signal<DailyGuidancePayload['panchanga_details'] | null>(null);
  protected readonly criticalTransits = signal<DailyGuidancePayload['context']['active_gochara']>([]);
  protected readonly muhurtaWindows = signal<DailyGuidancePayload['muhurta_windows']>([]);

  // Always shown. A reading whose conventions are hidden is not reproducible —
  // the same chart under a different ayanamsa is a different answer.
  readonly conventions = signal<string[]>([]);

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
  readonly statSections = signal<StatSection[]>([]);

  /** Openers for Ask, seeded from the day so the tab is not a blank prompt. */
  readonly askSuggestions = signal<string[]>([]);

  constructor() {
    effect(() => {
      const profilesLoaded = this.kundlis.loaded();
      const profileId = this.kundlis.activeId();
      // This read is the invalidation boundary for current-place guidance.
      this.preferences.panchangaContextKey();
      if (profilesLoaded) void this.loadToday(profileId);
    });
    if (!this.kundlis.loaded()) void this.kundlis.load();
    // Deep-linked from the onboarding Aha screen's "Listen to my first
    // guidance" — arriving with ?listen=1 should open the sheet immediately
    // rather than land on a plain Today with no explanation of the link.
    if (this.route.snapshot.queryParamMap.get('listen') === '1') {
      this.openSheet.set('listen');
    }
  }

  protected async loadToday(profileId = this.kundlis.activeId()): Promise<void> {
    const request = ++this.requestId;
    this.loadError.set(null);
    this.emptyProfile.set(false);
    try {
      const profile = this.kundlis.kundlis().find((item) => item.id === profileId) ?? null;
      if (!profile) {
        this.view.set(null);
        this.loading.set(false);
        this.emptyProfile.set(true);
        return;
      }
      const cached = this.vedic.cachedDailyGuidance(profile.id);
      if (cached) {
        if (request !== this.requestId || this.kundlis.activeId() !== profile.id) return;
        this.applyDaily(profile.name, profile.birth_city, cached);
        this.loading.set(false);
        void this.prefetchCalendar(profile.id);
        void this.prefetchChart(profile.id);
        void this.refreshToday(profile.id, request);
        return;
      }
      this.loading.set(true);
      const daily = await this.vedic.dailyGuidance(profile.id);
      if (request !== this.requestId || this.kundlis.activeId() !== profile.id) return;
      this.applyDaily(profile.name, profile.birth_city, daily);
      void this.prefetchCalendar(profile.id);
      void this.prefetchChart(profile.id);
    } catch (error) {
      if (request === this.requestId) this.loadError.set((error as Error).message);
    } finally {
      if (request === this.requestId) this.loading.set(false);
    }
  }

  private async refreshToday(profileId: string, request: number): Promise<void> {
    try {
      const daily = await this.vedic.refreshDailyGuidance(profileId);
      if (request !== this.requestId || this.kundlis.activeId() !== profileId) return;
      const profile = this.kundlis.active();
      if (profile) this.applyDaily(profile.name, profile.birth_city, daily);
    } catch {
      // Saved guidance remains usable when background refresh is unavailable.
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
      doItems: daily.do_today.length
        ? daily.do_today.map((row) => row.headline)
        : [daily.reading.best_for[0] ?? daily.reading.focus],
      avoidItems: daily.avoid_today.length
        ? daily.avoid_today.map((row) => row.headline)
        : [daily.reading.avoid[0] ?? daily.reading.timing_note],
      nextWindowLabel: 'TIMING NOTE',
      nextWindowValue: daily.reading.timing_note,
      nextWindowIn: muhurtaCountdown(daily),
    });
    this.loadedDaily.set({
      name,
      dateLabel,
      city: daily.provenance.place.city || city,
      daily,
    });
    this.signals.set([
      {
        name: 'Tarabala',
        verdict: daily.tarabala.favourable ? 'GOOD' : 'CAUTION',
        tone: daily.tarabala.favourable ? 'good' : 'warn',
        explanation: plainTarabala(daily),
      },
      {
        name: 'Chandrabala',
        verdict: daily.chandrabala.favourable ? 'GOOD' : 'CAUTION',
        tone: daily.chandrabala.favourable ? 'good' : 'warn',
        explanation: plainChandrabala(daily),
      },
      ...daily.context.active_gochara.slice(0, 1).map((transit) => ({
        name: transit.planet,
        verdict: transit.severity === 'high' ? 'USE CARE' : 'ACTIVE',
        tone: transit.severity === 'high' ? 'warn' as const : 'good' as const,
        explanation: transit.severity === 'high'
          ? `${transit.name} is active, so keep extra patience around the area it touches.`
          : `${transit.name} is active in the background today.`,
      })),
    ]);
    this.scoreReason.set(scoreReason(daily));
    this.summary.set(daily.reading.summary);
    // The full narrative leads the evidence sheet, so nothing the engine wrote
    // is dropped — it just stops overflowing the card it was never sized for.
    this.plainWords.set([daily.verdict.text, ...daily.reading.plain_why]);
    this.calculation.set(daily.reading.technical_why.map((value, index) => ({
      label: `Signal ${index + 1}`,
      value,
    })));
    this.references.set(daily.context.references);
    this.doAvoidExplained.set([
      ...daily.do_today.map((row) => ({ kind: 'do' as const, headline: row.headline, detail: row.text })),
      ...daily.avoid_today.map((row) => ({ kind: 'avoid' as const, headline: row.headline, detail: row.text })),
    ]);
    this.conventions.set([
      daily.system,
      this.preferences.ayanamsha(),
      `${daily.provenance.place.city} · ${daily.provenance.place.timezone}`,
    ]);
    this.dashaChain.set(daily.context.dasha_chain.map((level) => ({
      ...level,
      short: DASHA_LEVEL_SHORT[level.level] ?? level.level,
    })));
    this.panchangaDetails.set(daily.panchanga_details);
    this.criticalTransits.set(daily.context.active_gochara);
    this.muhurtaWindows.set(daily.muhurta_windows);
    this.statSections.set([
      {
        eyebrow: 'TODAY’S SKY · PANCHANG',
        columns: 2,
        cells: [
          { label: 'TITHI', value: daily.star_of_day.tithi, symbol: tithiSymbol(daily.star_of_day.tithi) },
          { label: 'NAKSHATRA', value: daily.star_of_day.nakshatra, symbol: nakshatraSymbol(daily.star_of_day.nakshatra) },
          { label: 'VARA', value: daily.vara },
          { label: 'MOON SIGN', value: daily.star_of_day.moon_rashi },
        ],
      },
      {
        eyebrow: 'TODAY · CHANGES DAILY',
        columns: 3,
        cells: [
          { label: 'COLOUR', value: daily.color.name, symbol: colorSymbol(daily.color.name, daily.color.hex) },
          { label: 'NUMBER', value: String(daily.number.value) },
          { label: 'TARABALA', value: daily.tarabala.favourable ? 'Good' : 'Caution' },
        ],
      },
      {
        eyebrow: 'ALWAYS · YOUR SIGNATURE',
        columns: 3,
        cells: [
          { label: 'LUCKY NO.', value: String(daily.lucky_numbers.astrological.number) },
          { label: 'GEM', value: daily.lucky_signature.gem, symbol: gemSymbol(daily.lucky_signature.gem) },
          { label: 'DIRECTION', value: daily.lucky_signature.direction, symbol: directionSymbol(daily.lucky_signature.direction) },
        ],
      },
    ]);
    // The third question leans into what this persona already sees on the
    // rest of the screen: Practitioner has AV bindus and a dasha chain right
    // there, so "explain this nakshatra in simple words" undersells it.
    const activePlanet = daily.context.active_gochara[0]?.planet;
    const currentDashaLord = daily.context.dasha_chain.at(-1)?.lord;
    const practitionerQuestion = activePlanet
      ? `What does ${activePlanet}'s current transit mean for my chart specifically?`
      : currentDashaLord
        ? `How is my ${currentDashaLord} period shaping today's reading?`
        : `Explain ${daily.star_of_day.nakshatra} nakshatra in simple words`;
    this.askSuggestions.set([
      `Why is today ${daily.verdict.tone === 'caution' ? 'a caution day' : 'supportive'} for me?`,
      // daily.reading.focus is a full coaching paragraph ("Downshift. This is
      // a day for..."), not a short phrase — grafting it into "with X today?"
      // read as a broken run-on. The question stands on its own instead.
      'What should today’s focus be for me?',
      this.preferences.experienceMode() === 'practitioner'
        ? practitionerQuestion
        : `Explain ${daily.star_of_day.nakshatra} nakshatra in simple words`,
    ]);
  }

  private async prefetchCalendar(profileId: string): Promise<void> {
    try {
      const calendar = await this.vedic.calendarIntelligence(profileId, 45);
      const place = this.preferences.panchangaPlace();
      const profile = this.kundlis.active();
      const city = place?.city || profile?.birth_city;
      const nation = place?.nation || profile?.birth_nation || 'IN';
      if (city) void this.festivals.upcoming(city, nation, calendar.start_date, 60);
    } catch {
      // Today should stay usable even if Calendar cannot be warmed in the background.
    }
  }

  private async prefetchChart(profileId: string): Promise<void> {
    try {
      this.natal.set(await this.vedic.all(profileId));
    } catch {
      // Today should stay usable even if the natal chart cannot be warmed.
    }
  }
}
