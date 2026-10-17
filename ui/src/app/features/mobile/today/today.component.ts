import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal, untracked } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { timingPlaceLabel } from '../../../core/timing-place';
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
import { ResourceFreshness } from '../../../core/resource-cache';
import { DailyBriefResponse, DailyGuidancePayload, VedicAll, DailyActionRow, FestivalOccurrence } from '../../../core/models';
import { FestivalSheetComponent } from '../calendar/festival-sheet.component';
import { AnalyticsService } from '../../../core/analytics.service';
import { TODAY_DRILL_DOWNS, whyDrillDowns } from '../why-reading/drill-downs';
import { FestivalService, festivalPlace } from '../../../core/festival.service';
import { ProfileSwitcherComponent } from '../profile-switcher/profile-switcher.component';
import { ExperienceMode, PreferencesService, ReadingTone } from '../../../core/preferences.service';
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

/**
 * The sun-rise intro is a once-per-launch moment. Module state, so it
 * survives Today being detached and re-attached by the route reuse strategy
 * (which restarts CSS animations) and Today being rebuilt.
 */
let todayIntroPlayed = false;
/** The last planet lands at 2.7 s + 0.52 s (today.component.scss). */
const TODAY_INTRO_MS = 3300;

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
export function muhurtaCountdown(daily: DailyGuidancePayload, now: Date = new Date()): string {
  const rahu = daily.muhurta_windows.find((w) => w.name.startsWith('Rahu Kalam'));
  if (!rahu) return '';
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: daily.provenance.place.timezone,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).formatToParts(now);
  const part = (type: string) => parts.find((p) => p.type === type)?.value ?? '';
  // The guidance is cached per day; only show a live countdown for the day
  // it actually describes, not a stale "starts in" on yesterday's cache.
  if (`${part('year')}-${part('month')}-${part('day')}` !== daily.date) return '';
  const nowMinutes = Number(part('hour')) * 60 + Number(part('minute'));
  const [start, end] = rahu.time.split(/[–-]/).map(minutesSinceMidnight);
  if (nowMinutes < start) return `Starts in ${formatDuration(start - nowMinutes)}`;
  if (nowMinutes < end) return `Ends in ${formatDuration(end - nowMinutes)}`;
  // Past for today: say so rather than leaving the note's corner blank.
  return 'Ended';
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
  presentation?: 'grid' | 'signature';
}

export interface TodayView {
  greetingName: string;
  initial: string;
  dateLabel: string;
  place: string;
  /** "Hyderabad (birth city)": which rule chose the place, for the label. */
  placeLong: string;
  score: number;
  band: DayBand;
  scoreLabel: string;
  verdict: string;
  detail: string;
  /** The agent's header for the card; the static eyebrow when absent. */
  cardTitle?: string;
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
/** The "Practically, … Overall, …" sentence that closes the day narrative, if present. */
function practicalClose(text: string): string[] {
  const at = text.indexOf('Practically,');
  return at >= 0 ? [text.slice(at).trim()] : [];
}

@Component({
  selector: 'as-today',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    BirthDetailsCardComponent,
    DayGaugeComponent,
    DayQualitySheetComponent,
    FestivalSheetComponent,
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
  protected readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  private readonly festivals = inject(FestivalService);
  private readonly analytics = inject(AnalyticsService);
  private readonly route = inject(ActivatedRoute);
  protected readonly preferences = inject(PreferencesService);

  /** Guided readers get the row without the tara label ("A steady, well-being day"). */
  private rowHeadline(row: DailyActionRow): string {
    return this.preferences.experienceMode() === 'guided' && row.plain_headline ? row.plain_headline : row.headline;
  }
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
  readonly cacheFreshness = signal<ResourceFreshness | null>(null);
  readonly cacheUpdatedAt = signal<number | null>(null);

  protected readonly headerInitial = computed(
    () => this.view()?.initial ?? this.kundlis.active()?.name.slice(0, 1).toUpperCase() ?? 'A',
  );
  protected readonly headerName = computed(
    () => this.view()?.greetingName ?? this.kundlis.active()?.name ?? 'there',
  );
  // The avatar beside the greeting carries whose chart this is.
  protected readonly headerDate = computed(() => this.view()?.dateLabel ?? 'Today');
  /** The day the guidance is for, which the timing note opens in the calendar. */
  protected readonly todayDate = computed(() => this.loadedDaily()?.daily.date ?? '');
  protected readonly greeting = computed(
    () => `Namaste, ${this.kundlis.owner()?.name.split(' ')[0] ?? this.headerName()}`,
  );
  protected readonly listenScript = computed(() =>
    this.audioSections().map((section) => section.text).join(' '),
  );
  private readonly loadedDaily = signal<{
    name: string;
    city: string;
    dateLabel: string;
    daily: DailyGuidancePayload;
  } | null>(null);
  /** The agent's brief for the loaded day, once it arrives; null until then. */
  private readonly agentBrief = signal<{ profileId: string; date: string; brief: NonNullable<DailyBriefResponse['brief']> } | null>(null);
  private briefRequest = 0;
  protected readonly audioSections = computed<AudioReadingSection[]>(() => {
    const loaded = this.loadedDaily();
    if (!loaded) return [];
    const agent = this.currentBrief(loaded.daily.date);
    if (agent?.spoken.length) return agent.spoken.map((section) => ({ ...section }));
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
  readonly openSheet = signal<'quality' | 'why' | 'listen' | 'festival' | null>(null);

  /**
   * The next festival or vrat within two weeks, for the one reminder card
   * Today carries now that Calendar is a Practitioner tab (checklist D1).
   * Filtered by the reader's festival regions, like the Calendar list.
   */
  readonly upcomingFestival = signal<FestivalOccurrence | null>(null);
  protected readonly festivalWhen = computed(() => {
    const festival = this.upcomingFestival();
    if (!festival) return '';
    const day = new Date(`${festival.occurs_on}T12:00:00`);
    const today = new Date();
    today.setHours(12, 0, 0, 0);
    const days = Math.round((day.getTime() - today.getTime()) / 86_400_000);
    const date = new Intl.DateTimeFormat('en', { weekday: 'short', day: 'numeric', month: 'short' }).format(day);
    return days <= 0 ? `Today · ${date}` : days === 1 ? `Tomorrow · ${date}` : `In ${days} days · ${date}`;
  });
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
  protected showSheet(kind: 'quality' | 'why' | 'listen' | 'festival'): void {
    this.haptics.tap();
    this.openSheet.set(kind);
    if (kind === 'why') this.analytics.track('why_opened', { surface: 'today' });
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

  /** "Show me why" links into the chart screens behind today's reading. */
  protected readonly drillDowns = computed(() =>
    whyDrillDowns([...this.calculation().map((row) => row.value), ...this.plainWords()], TODAY_DRILL_DOWNS));

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

  /**
   * The month under both reckonings, as chips. A purnimanta reader in Delhi
   * and an amanta reader in Hyderabad are looking at the same sky and must
   * both find their own month name here, with the rule used stated.
   */
  private masaChips(masa: DailyGuidancePayload['masa']): string[] {
    if (!masa?.amanta) return [];
    const adhika = masa.adhika ? 'Adhika ' : '';
    const chips = [`Amanta month: ${adhika}${masa.amanta}`];
    if (masa.purnimanta && masa.purnimanta !== masa.amanta) chips.push(`Purnimanta: ${adhika}${masa.purnimanta}`);
    if (masa.paksha) chips.push(`${masa.paksha} paksha`);
    chips.push('Amanta reckoning used');
    return chips;
  }

  /** Openers for Ask, seeded from the day so the tab is not a blank prompt. */
  readonly askSuggestions = signal<string[]>([]);

  /**
   * True once the intro has run this session. The sky then renders in its
   * final state with no entrance, so returning to the tab does not replay a
   * 3 s animation.
   */
  protected readonly introPlayed = signal(todayIntroPlayed);

  constructor() {
    // "Starts in / Ends in" is a countdown: recompute it each half minute, so
    // it moves (and turns to "Ended") while Today stays open.
    const tick = setInterval(() => {
      const loaded = this.loadedDaily();
      if (!loaded) return;
      const next = muhurtaCountdown(loaded.daily);
      this.view.update((view) => (view && view.nextWindowIn !== next ? { ...view, nextWindowIn: next } : view));
    }, 30_000);
    inject(DestroyRef).onDestroy(() => clearInterval(tick));
    if (!todayIntroPlayed) {
      todayIntroPlayed = true;
      const timer = setTimeout(() => this.introPlayed.set(true), TODAY_INTRO_MS);
      inject(DestroyRef).onDestroy(() => clearTimeout(timer));
    }
    effect(() => {
      const profilesLoaded = this.kundlis.loaded();
      const profileId = this.kundlis.activeId();
      // This read is the invalidation boundary for current-place guidance.
      this.preferences.panchangaContextKey();
      // Only the reads above may re-run this. loadToday reads and writes
      // loadedDaily and the brief; tracked, each load re-armed the effect and
      // Today rebuilt itself in a loop, which showed as constant flicker.
      if (profilesLoaded) untracked(() => void this.loadToday(profileId));
    });
    // The agent brief follows the loaded day and the reading style. A changed
    // tone or experience mode is a different brief, fetched (or reused) here.
    effect(() => {
      const loaded = this.loadedDaily();
      const profileId = this.kundlis.activeId();
      const tone = this.preferences.tone();
      const mode = this.preferences.experienceMode();
      if (loaded && profileId) untracked(() => void this.loadBrief(profileId, loaded.daily.date, tone, mode));
    });
    if (!this.kundlis.loaded()) void this.kundlis.load().catch(() => undefined);
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
      const cached = this.vedic.cachedDailyGuidanceEntry(profile.id);
      if (cached) {
        if (request !== this.requestId || this.kundlis.activeId() !== profile.id) return;
        this.applyDaily(profile.name, profile.birth_city, cached.data);
        this.cacheFreshness.set(cached.freshness);
        this.cacheUpdatedAt.set(cached.storedAt);
        this.loading.set(false);
        void this.prefetchCalendar(profile.id);
        void this.prefetchChart(profile.id);
        if (cached.freshness === 'stale') void this.refreshToday(profile.id, request);
        return;
      }
      // Nothing cached for this profile and place: clear the last one rather
      // than keep it on screen. After a city change the old city's Rahu Kalam
      // stayed up, counting down on the new clock, until the new day arrived.
      this.view.set(null);
      this.muhurtaWindows.set([]);
      this.panchangaDetails.set(null);
      this.loadedDaily.set(null);
      this.loading.set(true);
      const daily = await this.vedic.dailyGuidance(profile.id);
      if (request !== this.requestId || this.kundlis.activeId() !== profile.id) return;
      this.applyDaily(profile.name, profile.birth_city, daily);
      this.cacheFreshness.set('fresh');
      this.cacheUpdatedAt.set(Date.now());
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
      if (profile) {
        this.applyDaily(profile.name, profile.birth_city, daily);
        this.cacheFreshness.set('fresh');
        this.cacheUpdatedAt.set(Date.now());
      }
    } catch {
      // Saved guidance remains usable when background refresh is unavailable.
    }
  }

  protected cacheAgeLabel(): string {
    const updatedAt = this.cacheUpdatedAt();
    if (!updatedAt) return 'Saved guidance';
    return `Saved ${new Intl.DateTimeFormat('en', { hour: 'numeric', minute: '2-digit' }).format(updatedAt)}`;
  }

  private currentBrief(date: string): NonNullable<DailyBriefResponse['brief']> | null {
    const agent = this.agentBrief();
    return agent && agent.date === date && agent.profileId === this.kundlis.activeId() ? agent.brief : null;
  }

  private async loadBrief(profileId: string, date: string, tone: ReadingTone, mode: ExperienceMode): Promise<void> {
    const request = ++this.briefRequest;
    const current = this.agentBrief();
    if (current && (current.profileId !== profileId || current.date !== date)) this.agentBrief.set(null);
    try {
      const response = await this.vedic.dailyBrief(profileId, date, tone, mode, (fresh) => {
        if (request !== this.briefRequest || this.kundlis.activeId() !== profileId || !fresh.brief) return;
        this.agentBrief.set({ profileId, date, brief: fresh.brief });
        this.applyBrief();
      });
      if (request !== this.briefRequest || this.kundlis.activeId() !== profileId) return;
      if (!response.brief || response.date !== date) return;
      this.agentBrief.set({ profileId, date, brief: response.brief });
      this.applyBrief();
    } catch {
      // The templated brief is already on screen; it stays.
    }
  }

  /** Puts the agent's wording over the templated cards for the same day. */
  private applyBrief(): void {
    const loaded = this.loadedDaily();
    const brief = loaded ? this.currentBrief(loaded.daily.date) : null;
    if (!brief) return;
    this.view.update((view) => view && ({
      ...view,
      cardTitle: brief.card_title || undefined,
      verdict: brief.headline,
      detail: brief.summary,
      doItems: brief.do.map((item) => item.headline),
      avoidItems: brief.avoid.map((item) => item.headline),
      nextWindowValue: brief.timing_note,
    }));
    this.summary.set(brief.summary);
    this.plainWords.set([...brief.why, brief.practical_close]);
    this.doAvoidExplained.set([
      ...brief.do.map((item) => ({ kind: 'do' as const, headline: item.headline, detail: item.detail })),
      ...brief.avoid.map((item) => ({ kind: 'avoid' as const, headline: item.headline, detail: item.detail })),
    ]);
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
      placeLong: timingPlaceLabel(daily.provenance.place) || city,
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
        ? daily.do_today.map((row) => this.rowHeadline(row))
        : [daily.reading.best_for[0] ?? daily.reading.focus],
      avoidItems: daily.avoid_today.length
        ? daily.avoid_today.map((row) => this.rowHeadline(row))
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
      // Only Guru Bala is "supportive"; every medium rule (Kantaka Shani,
      // Rahu, Ketu, Mars from the Moon) is a caution, and was shown green
      // under an ACTIVE pill that read like GOOD (regression 2026-10-17, M3).
      ...daily.context.active_gochara.slice(0, 1).map((transit) => {
        const supportive = transit.severity === 'supportive';
        return {
          name: transit.planet,
          verdict: supportive ? 'GOOD' : transit.severity === 'high' ? 'USE CARE' : 'CAUTION',
          tone: supportive ? 'good' as const : 'warn' as const,
          explanation: supportive
            ? `${transit.name} is supporting you in the background today.`
            : transit.severity === 'high'
              ? `${transit.name} is active, so keep extra patience around the area it touches.`
              : `${transit.name} is active, a milder caution around the area it touches.`,
        };
      }),
    ]);
    this.scoreReason.set(scoreReason(daily));
    this.summary.set(daily.reading.summary);
    // plain_why already restates the narrative's three signals (tara, Moon,
    // transit) one per bullet, so leading with the whole narrative said the
    // transit twice. Keep the bullets and only the narrative's practical close.
    this.plainWords.set([...daily.reading.plain_why, ...practicalClose(daily.verdict.text)]);
    this.calculation.set(daily.reading.technical_why.map((value, index) => ({
      label: `Signal ${index + 1}`,
      value,
    })));
    this.references.set(daily.context.references);
    this.doAvoidExplained.set([
      ...daily.do_today.map((row) => ({ kind: 'do' as const, headline: this.rowHeadline(row), detail: row.text })),
      ...daily.avoid_today.map((row) => ({ kind: 'avoid' as const, headline: this.rowHeadline(row), detail: row.text })),
    ]);
    this.conventions.set([
      daily.system,
      this.preferences.ayanamsha(),
      `${daily.provenance.place.city} · ${daily.provenance.place.timezone}`,
      ...this.masaChips(daily.masa),
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
        eyebrow: 'YOUR BIRTH SIGNATURE',
        columns: 3,
        presentation: 'signature',
        cells: [
          // The chart-derived number (lagna lord). Labelled as such because the
          // Favourable screen also shows the numerology moolank, and both read as
          // "lucky number" when the method is not named.
          { label: 'CHART NUMBER', value: String(daily.lucky_numbers.astrological.number) },
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
    // A refresh rebuilds the view from the template; put the agent's words back.
    this.applyBrief();
  }

  private async prefetchCalendar(profileId: string): Promise<void> {
    try {
      const calendar = await this.vedic.calendarIntelligence(profileId, 45);
      const place = festivalPlace(this.preferences, this.kundlis.active());
      if (!place) return;
      const window = await this.festivals.upcoming(place, calendar.start_date, 60, this.preferences.festivalRegions());
      if (this.kundlis.activeId() !== profileId) return;
      const today = localIsoDate(new Date());
      const horizon = localIsoDate(new Date(Date.now() + 14 * 86_400_000));
      this.upcomingFestival.set(
        window.festivals
          .filter((festival) => festival.occurs_on >= today && festival.occurs_on <= horizon)
          .sort((a, b) => a.occurs_on.localeCompare(b.occurs_on))[0] ?? null,
      );
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

/** The phone's calendar date as `YYYY-MM-DD`; toISOString() would give UTC's. */
function localIsoDate(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}
