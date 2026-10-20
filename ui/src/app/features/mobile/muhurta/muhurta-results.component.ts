import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ReferOutError } from '../../../core/api.service';
import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';
import { timingClockNote, timingPlaceLabel } from '../../../core/timing-place';
import { AnalyticsService } from '../../../core/analytics.service';
import { addToCalendar as addEventToCalendar } from '../../../core/calendar-export';
import { MuhurtaApiWindow, MuhurtaSearchOptions, MuhurtaSearchPayload, VedicService } from '../../../core/vedic.service';
import { GenericErrorComponent } from '../states/generic-error.component';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { localIsoDate } from './muhurta-goal.component';

/** How strongly a window is endorsed, in words. */
export type WindowQuality = 'best' | 'good' | 'workable';

export const QUALITY_WORDS: Record<WindowQuality, string> = {
  best: 'Excellent',
  good: 'Good',
  workable: 'Usable',
};

export interface MuhurtaWindow {
  rank: number;
  date: string;
  quality: WindowQuality;
  qualityLabel: string;
  time: string;
  score: number;
  window: string;
  supports: string[];
  against: string[];
  /** The classical names behind the plain reasons. */
  terms: string[];
  badges: string[];
  tags: string[];
  /** The rule that produced this window, named. */
  reason: string;
  startIso: string;
  endIso: string;
}

/**
 * Each phrase completes "Best times to …", so every one has to be a verb
 * phrase. The goal *labels* are noun-ish ("Marriage-related") and cannot be
 * dropped in directly — doing so produced "Best times to for a marriage
 * matter".
 */
const GOAL_PHRASES: Record<string, string> = {
  buy_vehicle: 'buy or take delivery of a vehicle',
  buy_gold: 'buy gold or jewellery',
  buy_property_gold: 'buy property',
  property_registration: 'register property',
  sign_contract: 'sign a contract',
  start_venture: 'open a shop or business',
  join_job: 'join a new job',
  move_rented_home: 'move into a rented home',
  start_journey: 'start a journey',
  start_sadhana: 'start a vrat, japa or practice',
  griha_pravesha: 'do Griha Pravesha',
  bhoomi_puja: 'do bhoomi puja',
  upanayana: 'perform Upanayana',
  namakarana: 'hold Namakarana',
  annaprashana: 'hold Annaprashana',
  mundan: 'do the first haircut (mundan)',
  karnavedha: 'do ear piercing',
  seemantham: 'hold the baby shower',
  vidyarambha: 'begin learning',
  marriage_related: 'hold the wedding',
  engagement: 'hold the engagement',
  general: 'do what you’re planning',
};

const RANGE_LABELS: Record<string, string> = {
  week: 'This week',
  month: 'This month',
  fortnight: 'Next 2 weeks',
  custom: 'Your dates',
  date: 'Your date',
};

const PAGE = 8;

/**
 * Muhurta — Results (Figma node 31:57).
 *
 * Ranked times for one stated purpose. Each says, in plain words, what
 * supports it and what needs care, with the classical names one tap away
 * ("Why this time?") — those names are exactly the convention-dependent
 * part, and naming them lets a reader who follows another tradition see that
 * it is a different tradition, not a mistake. What the search left out
 * (night hours for a showroom, Chaturmas for a wedding) is said up top, so a
 * short list never reads as a broken one.
 *
 * The closing line — timing supports the intent, the decision and diligence
 * are still the reader's — is the screen's point, not its disclaimer.
 */
@Component({
  selector: 'as-muhurta-results',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackLinkDirective, GenericErrorComponent, RouterLink],
  templateUrl: './muhurta-results.component.html',
  styleUrl: './muhurta-results.component.scss',
})
export class MuhurtaResultsComponent {
  private readonly params = toSignal(inject(ActivatedRoute).queryParamMap, {
    requireSync: true,
  });
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  private readonly preferences = inject(PreferencesService);
  protected readonly loading = signal(true);
  protected readonly loadingMore = signal(false);
  protected readonly error = signal<string | null>(null);
  /** The backend's refer-out sentence for an excluded intent; not an error. */
  protected readonly referOut = signal<string | null>(null);
  protected readonly searched = signal(false);
  protected readonly notes = signal<string[]>([]);
  protected readonly nextGood = signal<MuhurtaSearchPayload['next_good']>(null);
  protected readonly moreAvailable = signal(0);
  protected readonly rulesNote = signal<string | null>(null);
  protected readonly observanceNote = signal<string | null>(null);
  protected readonly disclaimer = signal('Timing supports your intent; the decision and the care are still yours.');
  protected readonly open = signal<number | null>(null);
  protected readonly practitioner = computed(() => this.preferences.experienceMode() === 'practitioner');
  private limit = PAGE;

  protected readonly heading = computed(() => {
    const goal = this.params().get('goal') ?? 'sign_contract';
    const intent = this.params().get('intent')?.trim();
    const when = this.params().get('range') === 'date' ? ` on ${this.shortDate(this.params().get('date_from') ?? '')}` : '';
    if (goal === 'general' && intent) return `Best times for ${intent}${when}`;
    return `Best times to ${GOAL_PHRASES[goal] ?? GOAL_PHRASES['general']}${when}`;
  });

  protected readonly scope = computed(() => {
    const range = this.params().get('range') ?? 'month';
    // The place arrives with the results; until then it is left out rather
    // than leaving a trailing separator.
    return [RANGE_LABELS[range] ?? RANGE_LABELS['month'], this.dateScope(), this.place()].filter(Boolean).join(' · ');
  });

  /** Whose chart the times were checked against. */
  protected readonly forWhom = computed(() => {
    const names = [this.params().get('person'), this.params().get('partner')]
      .filter(Boolean)
      .map((id) => this.kundlis.kundlis().find((k) => k.id === id)?.name)
      .filter(Boolean);
    return names.length ? `Checked against ${names.join(' and ')}’s chart${names.length > 1 ? 's' : ''}.` : '';
  });

  readonly place = signal('');
  /** Whose clock the window times are in, stated under the list. */
  readonly clockNote = signal('');
  readonly conventionDependent = signal(false);

  readonly windows = signal<MuhurtaWindow[]>([]);
  /** Rank of the window whose calendar file is being made. */
  protected readonly exporting = signal<number | null>(null);
  /** Rank of the window whose export failed, so the note sits under it. */
  protected readonly exportFailed = signal<number | null>(null);

  /**
   * Hands one window to the phone's calendar (see core/calendar-export.ts).
   * The calendar app owns the reminder, so it fires even with this app
   * closed.
   */
  protected async addToCalendar(w: MuhurtaWindow): Promise<void> {
    this.exporting.set(w.rank);
    this.exportFailed.set(null);
    try {
      const title = this.heading().replace(/^Best times (to|for) /, '');
      await addEventToCalendar({
        uid: `muhurta-${w.startIso}@astrospace`,
        title: `Muhurta: ${title}`,
        startIso: w.startIso,
        endIso: w.endIso,
        description: `${w.reason} ${this.disclaimer()}`,
        location: this.place(),
        alarmMinutes: 30,
      }, `muhurta-${w.startIso.slice(0, 10)}.ics`);
      this.analytics.track('calendar_exported', { source: 'muhurta' });
    } catch {
      this.exportFailed.set(w.rank);
    } finally {
      this.exporting.set(null);
    }
  }

  private readonly analytics = inject(AnalyticsService);

  constructor() {
    void this.load();
  }

  protected retry(): void {
    void this.load();
  }

  protected showMore(): void {
    this.limit += PAGE;
    void this.load(true);
  }

  protected toggle(rank: number): void {
    this.open.set(this.open() === rank ? null : rank);
  }

  private async load(more = false): Promise<void> {
    (more ? this.loadingMore : this.loading).set(true);
    this.error.set(null);
    this.referOut.set(null);
    if (!more) this.searched.set(false);
    try {
      await this.kundlis.load();
      const p = this.params();
      const activeId = p.get('person') || this.kundlis.activeId();
      if (!activeId) {
        this.windows.set([]);
        return;
      }
      const goal = p.get('goal') ?? 'sign_contract';
      const dateFrom = p.get('date_from') ?? localIsoDate(new Date());
      const dateTo = p.get('date_to') ?? localIsoDate(addDays(new Date(), 30));
      const eventCity = p.get('city');
      const place = eventCity ? { city: eventCity, nation: p.get('nation') ?? 'IN' } : this.preferences.panchangaPlace();
      const intent = goal === 'general' ? p.get('intent') : null;
      const options: MuhurtaSearchOptions = {
        partnerId: p.get('partner'),
        ceremony: (p.get('ceremony') as MuhurtaSearchOptions['ceremony']) ?? null,
        direction: (p.get('direction') as MuhurtaSearchOptions['direction']) ?? null,
        avoid: (p.get('avoid') ?? '').split(',').filter(Boolean),
        observeSeason: p.get('season') !== 'off',
      };
      const payload = await this.vedic.muhurta(activeId, goal, dateFrom, dateTo, place, this.limit, intent, options);
      this.place.set(timingPlaceLabel(payload.place) || (place ? `${place.city}, ${place.nation}` : 'birth city'));
      this.clockNote.set(timingClockNote(payload.place));
      this.notes.set(payload.notes ?? (payload.note ? [payload.note] : []));
      this.nextGood.set(payload.next_good ?? null);
      this.moreAvailable.set(payload.more_available ?? 0);
      this.observanceNote.set(payload.observance_note ?? null);
      this.rulesNote.set(goal === 'general' && intent && payload.rules_goal && payload.rules_goal !== 'general'
        ? `For “${intent}” we used the rules for: ${payload.rules_label}.`
        : null);
      this.disclaimer.set(payload.disclaimer);
      this.conventionDependent.set(!!payload.is_convention_dependent);
      this.windows.set(this.extractWindows(payload.results));
    } catch (error) {
      if (error instanceof ReferOutError) this.referOut.set(error.message);
      else this.error.set((error as Error).message);
    } finally {
      this.searched.set(true);
      this.loading.set(false);
      this.loadingMore.set(false);
    }
  }

  private extractWindows(results: MuhurtaApiWindow[]): MuhurtaWindow[] {
    return results.map((window, index) => {
      const quality: WindowQuality = window.quality ?? 'workable';
      const tags = [
        window.night ? 'Night' : null,
        window.weekend ? 'Weekend' : null,
      ].filter(Boolean) as string[];
      return {
        rank: index + 1,
        date: this.dateLabel(window.date),
        quality,
        qualityLabel: window.label ?? QUALITY_WORDS[quality],
        time: `${window.start} – ${window.end}`,
        score: window.score,
        window: window.window,
        supports: window.why.supports,
        against: window.why.against,
        terms: window.why.terms ?? [],
        badges: window.badges ?? [],
        tags,
        reason: this.reason(window),
        startIso: window.start_iso,
        endIso: window.end_iso,
      };
    });
  }

  private reason(window: MuhurtaApiWindow): string {
    const parts = [
      window.vara ?? null,
      window.nakshatra ? `${window.nakshatra} nakshatra` : null,
      window.trimmed ? 'shortened around times to avoid' : null,
    ].filter(Boolean) as string[];
    if (!parts.length) return '';
    const text = parts.join(' · ');
    return `${text.charAt(0).toUpperCase()}${text.slice(1)}.`;
  }

  protected dateLabel(value: string): string {
    const date = new Date(`${value}T12:00:00`);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString('en-IN', { weekday: 'long', month: 'long', day: 'numeric' });
  }

  private dateScope(): string {
    const from = this.params().get('date_from');
    const to = this.params().get('date_to');
    if (!from || !to) return 'next 30 days';
    if (from === to) return this.shortDate(from);
    return `${this.shortDate(from)} - ${this.shortDate(to)}`;
  }

  protected shortDate(value: string): string {
    const date = new Date(`${value}T12:00:00`);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
  }
}

function addDays(date: Date, days: number): Date {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}
