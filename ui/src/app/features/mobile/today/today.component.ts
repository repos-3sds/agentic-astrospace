import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, afterNextRender, computed, effect, inject, signal, untracked } from '@angular/core';
import { NgTemplateOutlet } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, NavigationEnd, Router, RouterLink } from '@angular/router';
import { timingPlaceHint, timingPlaceLabel } from '../../../core/timing-place';
import { DayGaugeComponent } from '../day-gauge/day-gauge.component';
import { DayQualitySheetComponent, DaySignal } from './day-quality-sheet.component';
import { ListenSheetComponent } from './listen-sheet.component';
import {
  DoAvoidExplainer,
  EvidenceRow,
  SourceReference,
  WhyReadingSheetComponent,
} from '../why-reading/why-reading-sheet.component';
import { NaturalVoiceService } from '../../../core/natural-voice.service';
import { KundliStore } from '../../../core/kundli.store';
import { BirthDetailsCardComponent } from '../chart/birth-details-card.component';
import { VedicService } from '../../../core/vedic.service';
import { ResourceFreshness } from '../../../core/resource-cache';
import { DailyBriefResponse, DailyGuidancePayload, DayScoreParts, DayScorePeriod, VedicAll, DailyActionRow, FestivalOccurrence } from '../../../core/models';
import { FestivalSheetComponent } from '../calendar/festival-sheet.component';
import { AnalyticsService } from '../../../core/analytics.service';
import { TODAY_DRILL_DOWNS, whyDrillDowns } from '../why-reading/drill-downs';
import { FestivalService, festivalPlace } from '../../../core/festival.service';
import { WidgetBridgeService, windowSpan } from '../../../core/widget-bridge.service';
import { ProfileSwitcherComponent } from '../profile-switcher/profile-switcher.component';
import { ReadingForComponent } from '../shared/reading-for.component';
import { NotifyNudgeComponent } from './notify-nudge.component';
import { ExperienceMode, PreferencesService, ReadingTone } from '../../../core/preferences.service';
import { HapticsService } from '../../../core/haptics.service';
import { PullRefreshService } from '../../../core/pull-refresh.service';
import { SubhashitaService } from '../../../core/subhashita.service';
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

// Matches $m-wide in mobile-tokens.scss, where Today becomes two columns.
const TWO_COLUMNS: MediaQueryList | null = globalThis.matchMedia?.('(min-width: 900px)') ?? null;

/** Figma 212:751's dasha-chain chips ("Moon Mahā › Rahu Antar › Jup Prat › Ven Sookshma"). */
const DASHA_LEVEL_SHORT: Record<string, string> = {
  mahadasha: 'Mahā',
  antardasha: 'Antar',
  pratyantardasha: 'Prat',
  sookshmadasha: 'Sookshma',
};

/**
 * Where the day sits on the 0-100 dial.
 *
 * The engine scores the day 0-100 with an ordinary day near 50 (see
 * _score_day in astrospace/context/daily.py) and sends it as day_score;
 * `score` stays the old signed tally for builds that still draw from it. A
 * reading from 2026-10-28 before that split has the 0-100 in `score` beside
 * score_parts. Anything older has only the tally; its band is placed in that
 * band's slice of the dial, so the ring and the label still agree.
 */
export function dayScorePosition(verdict: DailyGuidancePayload['verdict'], now: number = Date.now()): number {
  const clamp = (value: number) => Math.round(Math.min(100, Math.max(0, value)));
  const part = scorePeriodAt(verdict, now);
  if (part) return clamp(part.day_score);
  if (verdict.day_score != null) return clamp(verdict.day_score);
  if (verdict.score_parts) return clamp(verdict.score);
  const legacy: Record<DailyGuidancePayload['verdict']['tone'], number> = {
    supportive: 75, positive: 58, mixed: 40, caution: 25,
  };
  return legacy[verdict.tone];
}

export const BAND_OF_TONE: Record<DailyGuidancePayload['verdict']['tone'], DayBand> = {
  supportive: 'good', positive: 'steady', mixed: 'mixed', caution: 'tough',
};

/**
 * The part of the day in force at `now`, on a day the star or the Moon's sign
 * changes (verdict.day_score_periods, from 2026-10-30). The ring shows this
 * part's score and switches at the change; the sheet shows every part (Hawk,
 * 2026-10-30). Null on a day of one part, or a reading from before.
 */
export function scorePeriodAt(verdict: DailyGuidancePayload['verdict'], now: number = Date.now()): DayScorePeriod | null {
  const periods = verdict.day_score_periods ?? [];
  if (periods.length < 2) return null;
  return periods.find((p) => !p.until_iso || now < Date.parse(p.until_iso)) ?? periods[periods.length - 1];
}

/** The band of the part of the day in force now. */
export function dayBandAt(verdict: DailyGuidancePayload['verdict'], now: number = Date.now()): DayBand {
  return BAND_OF_TONE[scorePeriodAt(verdict, now)?.tone ?? verdict.tone];
}

/** "11:34 am" on the timings place's clock. */
export function clockLabel(iso: string, timeZone?: string): string {
  return new Intl.DateTimeFormat('en', { hour: 'numeric', minute: '2-digit', timeZone: timeZone || undefined })
    .format(new Date(iso)).toLowerCase();
}

/**
 * A change after 9 pm happens while most readers are winding down, so it
 * does not split the day's lines (the engine's _AWAKE_UNTIL).
 */
function startsAwake(iso: string | null, timeZone?: string): boolean {
  if (!iso) return false;
  const hour = Number(new Intl.DateTimeFormat('en', { hour: 'numeric', hourCycle: 'h23', timeZone: timeZone || undefined })
    .format(new Date(iso)));
  return hour < 21;
}

function wakingParts<T extends { from_iso: string | null }>(periods: T[] | undefined, timeZone?: string): T[] {
  return (periods ?? []).filter((p, i) => i === 0 || startsAwake(p.from_iso, timeZone));
}

/** One part of the day in the score sheet: "Until 11:34 am · 66 Steady". */
export interface DayPart {
  when: string;
  score: number;
  band: DayBand;
  label: string;
  why: string;
  current: boolean;
}

export function dayParts(daily: DailyGuidancePayload, now: number = Date.now()): DayPart[] {
  const tz = daily.provenance.place.timezone;
  const parts = wakingParts(daily.verdict.day_score_periods, tz);
  if (parts.length < 2) return [];
  const current = scorePeriodAt(daily.verdict, now);
  return parts.map((part, i) => {
    const next = parts[i + 1];
    const when = i === 0
      ? `Until ${clockLabel(next.from_iso!, tz)}`
      : next ? `${clockLabel(part.from_iso!, tz)} to ${clockLabel(next.from_iso!, tz)}` : `From ${clockLabel(part.from_iso!, tz)}`;
    const band = BAND_OF_TONE[part.tone];
    const star = part.tara ? `${part.tara} star, ${part.tara_favourable ? 'kind to you' : 'asks for care'}` : '';
    const moon = part.chandrashtama ? 'the Moon in a sensitive place' : '';
    return {
      when,
      score: Math.round(Math.min(100, Math.max(0, part.day_score))),
      band,
      label: BAND_LABEL[band],
      why: [star, moon].filter(Boolean).join(', and '),
      current: current?.from_iso === part.from_iso,
    };
  });
}

/** The tara in force at `now` (the reading may have been fetched before it changed). */
function taraNow(daily: DailyGuidancePayload, now: number): { favourable: boolean } {
  const periods = daily.tarabala_periods ?? [];
  return periods.find((p) => !p.until_iso || now < Date.parse(p.until_iso)) ?? daily.tarabala;
}

/** "Kind until 11:34 am, then asks for care." when the star changes in the waking day. */
function tarabalaChange(daily: DailyGuidancePayload): string {
  const tz = daily.provenance.place.timezone;
  const taras = wakingParts(daily.tarabala_periods, tz);
  if (taras.length < 2) return '';
  const word = (favourable: boolean) => (favourable ? 'is kind to you' : 'asks for care');
  const lines = taras.map((t, i) => i === 0
    ? `Your star (${t.tara}) ${word(t.favourable)} until ${clockLabel(taras[1].from_iso!, tz)}.`
    : `From ${clockLabel(t.from_iso!, tz)}, ${t.tara} ${word(t.favourable)}.`);
  return lines.join(' ');
}

/**
 * The next change of star still ahead today, for the Timing card: the
 * window that matters most when the day turns (Hawk asked that Timings show
 * it, 2026-10-30). Empty once it has passed.
 */
export function starChangeNote(daily: DailyGuidancePayload, now: number = Date.now()): { value: string; in: string } | null {
  const tz = daily.provenance.place.timezone;
  const next = wakingParts(daily.tarabala_periods, tz).slice(1).find((t) => t.from_iso && Date.parse(t.from_iso) > now);
  if (!next) return null;
  const at = clockLabel(next.from_iso!, tz);
  const value = next.favourable
    ? `Your star turns kinder at ${at}. Keep big starts for after then.`
    : `Your star turns less kind at ${at}. Do the important things before then.`;
  const minutes = Math.round((Date.parse(next.from_iso!) - now) / 60_000);
  return { value, in: `In ${formatDuration(Math.max(1, minutes))}` };
}

/** Today's first Ask chip, worded from the band so it never contradicts the ring (sweep F-9). */
const ASK_DAY_QUESTION: Record<DailyGuidancePayload['verdict']['tone'], string> = {
  supportive: 'Why is today supportive for me?',
  positive: 'Why is today a steady day for me?',
  mixed: 'Why is today a mixed day for me?',
  caution: 'Why should I go gently today?',
};

export const BAND_LABEL: Record<DayBand, string> = {
  good: 'Good', steady: 'Steady', mixed: 'Mixed', tough: 'Go gently',
};

/** "Why today is a 55", in words: which of the three signals lifted it and which held it back. */
function scoreReasonFromParts(parts: DayScoreParts): string {
  const up: string[] = [];
  const down: string[] = [];
  (parts.star > 0 ? up : down).push(parts.star > 0 ? 'the day’s star is with you' : 'the day’s star is not with you');
  if (parts.moon > 0) up.push('your Moon is steady');
  else down.push(parts.moon <= -12 ? 'the Moon is in a sensitive place for you' : 'your Moon is quieter than usual');
  if (parts.transits > 0) up.push('the slow planets are helping');
  if (parts.transits < 0) down.push('the slow planets add some pressure');
  const join = (items: string[]) => items.length > 1 ? `${items.slice(0, -1).join(', ')} and ${items.at(-1)}` : items[0];
  const sentences = ['Every day starts at 50.'];
  if (up.length) sentences.push(`It goes up because ${join(up)}.`);
  if (down.length) sentences.push(`${up.length ? 'It comes down because' : 'It comes down today because'} ${join(down)}.`);
  if ((parts.care ?? 0) < 0) sentences.push('The calendar marks today as a day to take care, so the score stays under 50.');
  return sentences.join(' ');
}

function scoreReason(daily: DailyGuidancePayload): string {
  const parts = scorePeriodAt(daily.verdict)?.day_score_parts ?? daily.verdict.day_score_parts ?? daily.verdict.score_parts;
  if (parts) return scoreReasonFromParts(parts);
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

/**
 * Between midnight and sunrise the date is already today but its panchang
 * day has not begun: the tithi, star and day lord shown are from today's
 * sunrise. Say when that is rather than imply they are already in force.
 * The time is on the timings place's clock, like every window on Today.
 */
export function sunriseNote(daily: DailyGuidancePayload, now: number = Date.now()): string {
  const sunrise = daily.valid_from ? Date.parse(daily.valid_from) : Number.NaN;
  if (!Number.isFinite(sunrise) || now >= sunrise) return '';
  const time = new Intl.DateTimeFormat('en', {
    hour: 'numeric',
    minute: '2-digit',
    timeZone: daily.provenance.place.timezone || undefined,
  }).format(new Date(sunrise));
  return `Today's panchang begins at sunrise, ${time.toLowerCase()}.`;
}

/** Verdict bands. Named, not numeric, so tone rules can key off them. */
export type DayBand = 'good' | 'steady' | 'mixed' | 'tough';

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

/** The place-hint wording last dismissed; a new city or reason shows again. */
const PLACE_HINT_KEY = 'as.today.place-hint-dismissed';

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
    ReadingForComponent,
    NotifyNudgeComponent,
    NgTemplateOutlet,
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
  private readonly widgets = inject(WidgetBridgeService);
  private readonly analytics = inject(AnalyticsService);
  private readonly route = inject(ActivatedRoute);
  protected readonly preferences = inject(PreferencesService);

  /** Guided readers get the row without the tara label ("A steady, well-being day"). */
  private rowHeadline(row: DailyActionRow): string {
    return this.preferences.experienceMode() === 'guided' && row.plain_headline ? row.plain_headline : row.headline;
  }
  private readonly haptics = inject(HapticsService);
  protected readonly subhashita = inject(SubhashitaService);
  private requestId = 0;
  /** Whose reading is on screen, so a switch knows to clear the last person's. */
  private shownProfileId: string | null = null;
  protected readonly whyMode = computed(() => ({
    guided: 'Guided view - the life guidance first, with unfamiliar terms translated.',
    balanced: 'Balanced view: guidance first, the calculation underneath.',
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

  /** The clock, moved on by the half-minute tick. */
  private readonly now = signal(Date.now());
  /** Where the part of the day the ring shows began; it redraws when this moves. */
  private scorePart: string | null = null;
  /** The day's parts, for the score sheet, when the star or Moon changes. */
  readonly dayParts = signal<DayPart[]>([]);

  /** Before sunrise, when today's panchang begins. */
  protected readonly sunriseNote = computed(() => {
    const daily = this.loadedDaily()?.daily;
    return daily ? sunriseNote(daily, this.now()) : '';
  });

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

  /** True while Today shows two columns (the m-wide breakpoint, 900px). */
  private readonly twoColumns = signal(TWO_COLUMNS?.matches ?? false);

  /**
   * On a wide tablet the day column ended at "Why this reading?" while the
   * other column ran on through the panchang and birth signature, leaving a
   * tall empty space on the left (Hawk, iPad, 2026-10-28). When the right
   * column is the long one, the Subhashita and "Reflect with Siddha" move
   * under the day card instead. Guided keeps its details shut, so its
   * columns are already even until the reader opens them. Phones keep one
   * column in the old order.
   */
  readonly fillDayColumn = computed(() =>
    this.twoColumns() && (this.preferences.experienceMode() !== 'guided' || this.detailsOpen()));

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
  /** "Times are for Toronto, a guess…": shown until the reader dismisses that wording. */
  protected readonly placeHint = signal('');

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
    if (TWO_COLUMNS) {
      const follow = (event: MediaQueryListEvent) => this.twoColumns.set(event.matches);
      TWO_COLUMNS.addEventListener('change', follow);
      inject(DestroyRef).onDestroy(() => TWO_COLUMNS.removeEventListener('change', follow));
    }
    inject(DestroyRef).onDestroy(inject(PullRefreshService).register('/m/today', () => this.pullRefresh()));
    // Ask early whether this reader has the natural voice, so Listen opens
    // already knowing which voice to use (the answer is kept for 10 minutes).
    void inject(NaturalVoiceService).available().catch(() => false);
    // "Starts in / Ends in" is a countdown: recompute it each half minute, so
    // it moves (and turns to "Ended") while Today stays open.
    const tick = setInterval(() => {
      this.now.set(Date.now());
      if (this.followDayChange()) return;
      const loaded = this.loadedDaily();
      if (!loaded) return;
      // The star or the Moon's sign changed since the ring was drawn, or the
      // change the Timing card counts down to has come: redraw the day.
      const starChange = starChangeNote(loaded.daily);
      if ((scorePeriodAt(loaded.daily.verdict)?.from_iso ?? null) !== this.scorePart
        || (!starChange && this.view()?.nextWindowLabel === 'YOUR STAR CHANGES')) {
        this.applyDaily(loaded.name, loaded.city, loaded.daily);
        this.applyBrief();
        return;
      }
      const next = starChange?.in ?? muhurtaCountdown(loaded.daily);
      this.view.update((view) => (view && view.nextWindowIn !== next ? { ...view, nextWindowIn: next } : view));
    }, 30_000);
    inject(DestroyRef).onDestroy(() => clearInterval(tick));
    // Today is a retained tab and the app is often left open overnight: on
    // coming back after midnight it showed the day before until something
    // else reloaded it. Check the date the moment the app is in view again.
    const visible = () => {
      if (document.visibilityState !== 'visible') return;
      this.now.set(Date.now());
      this.followDayChange();
    };
    document.addEventListener('visibilitychange', visible);
    inject(DestroyRef).onDestroy(() => document.removeEventListener('visibilitychange', visible));
    // The sky is position: fixed, but iOS WebKit clips fixed descendants of an
    // overflow scroller to the scroller's box. Inside the shell's .content it
    // stopped at the status bar, leaving a flat band behind the clock. Lifting
    // it into .shell (not a scroller) lets it run up behind the clock on both
    // platforms; Android already painted it there.
    const host = inject<ElementRef<HTMLElement>>(ElementRef, { optional: true })?.nativeElement;
    let sky: HTMLElement | null = null;
    afterNextRender(() => {
      sky = host?.querySelector<HTMLElement>(':scope > .celestial-sky') ?? null;
      if (sky) host?.closest('.shell')?.prepend(sky);
    });
    // Lifted out of Today's host, the sky no longer leaves with it. Today is a
    // retained tab root: navigating away detaches its view without destroying
    // it, and the sky stayed painted over every other screen (its sun sat on
    // the back arrow). Show it only while Today itself is in the page.
    const navigations = inject(Router).events.subscribe((event) => {
      if (event instanceof NavigationEnd && sky) sky.hidden = !host?.isConnected;
    });
    inject(DestroyRef).onDestroy(() => {
      navigations.unsubscribe();
      sky?.remove();
    });
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
    // guidance", and from the iPhone Listen widget — arriving with ?listen=1
    // should open the sheet immediately rather than land on a plain Today
    // with no explanation of the link. The widget can open it while Today is
    // already showing, so this follows the query, not just the first one.
    this.route.queryParamMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      if (params.get('listen') === '1') this.openSheet.set('listen');
    });
  }

  /** Load the new day once the reader's date has passed the one on screen. */
  private followDayChange(): boolean {
    const loaded = this.loadedDaily();
    if (!loaded || this.loading() || loaded.daily.date >= this.vedic.todayKey()) return false;
    void this.loadToday();
    return true;
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
      if (profile.id !== this.shownProfileId) {
        // A different person: nothing of the last one may stay up under the
        // new name. The birth card kept the previous profile's date, place
        // and lagna until the new chart arrived (2026-10-28).
        this.shownProfileId = profile.id;
        this.natal.set(this.vedic.cachedAll(profile.id));
        this.upcomingFestival.set(null);
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
      // The chart and calendar do not depend on the day: ask for all three
      // at once rather than one round trip after another.
      void this.prefetchCalendar(profile.id);
      void this.prefetchChart(profile.id);
      const daily = await this.vedic.dailyGuidance(profile.id);
      if (request !== this.requestId || this.kundlis.activeId() !== profile.id) return;
      this.applyDaily(profile.name, profile.birth_city, daily);
      this.cacheFreshness.set('fresh');
      this.cacheUpdatedAt.set(Date.now());
    } catch (error) {
      if (request === this.requestId) this.loadError.set((error as Error).message);
    } finally {
      if (request === this.requestId) this.loading.set(false);
    }
  }

  /**
   * Pulled down: fetch today again past the cache. With nothing on screen
   * (an error, or a first load still out) it is the ordinary load instead.
   */
  private async pullRefresh(): Promise<void> {
    const profileId = this.kundlis.activeId();
    if (!profileId) return;
    if (!this.view() || this.loadError()) return this.loadToday(profileId);
    return this.refreshToday(profileId, ++this.requestId);
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
      // The star's change, while it is ahead, outranks the brief's note.
      nextWindowValue: view.nextWindowLabel === 'YOUR STAR CHANGES' ? view.nextWindowValue : brief.timing_note,
    }));
    this.summary.set(brief.summary);
    this.plainWords.set([...brief.why, brief.practical_close]);
    this.doAvoidExplained.set([
      ...brief.do.map((item) => ({ kind: 'do' as const, headline: item.headline, detail: item.detail })),
      ...brief.avoid.map((item) => ({ kind: 'avoid' as const, headline: item.headline, detail: item.detail })),
    ]);
    this.publishWidget();
  }

  /**
   * The home-screen widgets show the account holder's own day, whichever
   * chart was last open: a widget that changed person with the profile
   * picker would read as the phone owner's day when it isn't.
   */
  private publishWidget(): void {
    const loaded = this.loadedDaily();
    const view = this.view();
    const owner = this.kundlis.owner();
    if (!this.widgets.enabled || !loaded || !view || !owner || owner.id !== this.kundlis.activeId()) return;
    const { daily } = loaded;
    const timeZone = daily.provenance.place.timezone;
    this.widgets.publishToday({
      date: daily.date,
      score: view.score,
      // The widgets draw three colours; Good shares Steady's.
      band: view.band === 'good' ? 'steady' : view.band,
      label: view.scoreLabel,
      headline: view.verdict,
      summary: view.detail,
      doItem: view.doItems[0] ?? '',
      avoidItem: view.avoidItems[0] ?? '',
      doItems: view.doItems.slice(0, 2),
      avoidItems: view.avoidItems.slice(0, 2),
      tithi: daily.star_of_day.tithi,
      nakshatra: daily.star_of_day.nakshatra,
      yoga: daily.panchanga_details?.yoga ?? '',
      moonSign: daily.star_of_day.moon_rashi,
      masa: widgetMasa(daily.masa),
      // The reading is valid from sunrise to the next sunrise.
      sunriseMs: daily.valid_from ? Date.parse(daily.valid_from) || null : null,
      windows: daily.muhurta_windows.flatMap((w) => {
        const span = timeZone ? windowSpan(daily.date, w.time, timeZone) : null;
        return span ? [{ name: w.name, kind: w.kind, ...span }] : [];
      }),
      listen: this.listenScript(),
    });
    void this.widgets.publishListenAudio(
      daily.date,
      this.listenScript(),
      this.audioSections().map((section) => section.text).filter((text) => text.trim()),
    );
  }

  protected dismissPlaceHint(): void {
    const hint = this.placeHint();
    if (!hint) return;
    try {
      localStorage.setItem(PLACE_HINT_KEY, hint);
    } catch {
      // Private mode: the hint simply comes back next time.
    }
    this.placeHint.set('');
  }

  private hintDismissed(hint: string): boolean {
    try {
      return localStorage.getItem(PLACE_HINT_KEY) === hint;
    } catch {
      return false;
    }
  }

  private applyDaily(name: string, city: string, daily: DailyGuidancePayload): void {
    const now = Date.now();
    const band = dayBandAt(daily.verdict, now);
    this.scorePart = scorePeriodAt(daily.verdict, now)?.from_iso ?? null;
    const starChange = starChangeNote(daily, now);
    const dateLabel = new Intl.DateTimeFormat('en', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      timeZone: 'UTC',
    }).format(new Date(`${daily.date}T00:00:00Z`));
    const hint = timingPlaceHint(daily.provenance.place);
    this.placeHint.set(hint && !this.hintDismissed(hint) ? hint : '');
    this.view.set({
      greetingName: name,
      initial: name.slice(0, 1).toUpperCase(),
      dateLabel,
      place: daily.provenance.place.city || city,
      placeLong: timingPlaceLabel(daily.provenance.place) || city,
      score: dayScorePosition(daily.verdict, now),
      band,
      scoreLabel: BAND_LABEL[band],
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
      nextWindowLabel: starChange ? 'YOUR STAR CHANGES' : 'TIMING NOTE',
      nextWindowValue: starChange?.value ?? daily.reading.timing_note,
      nextWindowIn: starChange?.in ?? muhurtaCountdown(daily),
    });
    this.dayParts.set(dayParts(daily, now));
    this.loadedDaily.set({
      name,
      dateLabel,
      city: daily.provenance.place.city || city,
      daily,
    });
    this.signals.set([
      {
        name: 'Tarabala',
        verdict: taraNow(daily, now).favourable ? 'GOOD' : 'CAUTION',
        tone: taraNow(daily, now).favourable ? 'good' : 'warn',
        explanation: tarabalaChange(daily) || plainTarabala(daily),
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
      ASK_DAY_QUESTION[daily.verdict.tone],
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
    this.publishWidget();
  }

  private async prefetchCalendar(profileId: string): Promise<void> {
    try {
      const calendar = await this.vedic.calendarIntelligence(profileId, 45);
      const place = festivalPlace(this.preferences, this.kundlis.owner() ?? this.kundlis.active());
      if (!place) return;
      const window = await this.festivals.upcoming(place, calendar.start_date, 60, this.preferences.festivalRegions());
      if (this.kundlis.activeId() !== profileId) return;
      if (this.kundlis.owner()?.id === profileId) void this.widgets.publishCalendar(place, calendar.start_date, window.festivals, { profileId, days: calendar.panchanga_days });
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
      const natal = await this.vedic.all(profileId);
      if (this.kundlis.activeId() === profileId) this.natal.set(natal);
    } catch {
      // Today should stay usable even if the natal chart cannot be warmed.
    }
  }
}

/** The phone's calendar date as `YYYY-MM-DD`; toISOString() would give UTC's. */
function localIsoDate(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

/**
 * The month line for the calendar widget. Which month a day falls in depends
 * on the reckoning (Amanta or Purnimanta), so the line names the rule it uses.
 */
export function widgetMasa(masa: DailyGuidancePayload['masa']): string {
  if (!masa?.amanta) return '';
  const month = `${masa.adhika ? 'Adhika ' : ''}${masa.amanta} (Amanta)`;
  return masa.paksha ? `${month} · ${masa.paksha} paksha` : month;
}
