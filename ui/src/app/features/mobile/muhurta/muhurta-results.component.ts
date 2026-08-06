import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';
import { MuhurtaApiWindow, VedicService } from '../../../core/vedic.service';

/** How strongly a window is endorsed. Two levels, not a score. */
export type WindowQuality = 'best' | 'good';

export interface MuhurtaWindow {
  rank: number;
  date: string;
  quality: WindowQuality;
  time: string;
  score: number;
  window: string;
  supports: string[];
  against: string[];
  /** The rule that produced this window, named. */
  reason: string;
}

/**
 * Each phrase completes "Best times to …", so every one has to be a verb
 * phrase. The goal *labels* are noun-ish ("Marriage-related") and cannot be
 * dropped in directly — doing so produced "Best times to for a marriage
 * matter".
 */
const GOAL_PHRASES: Record<string, string> = {
  buy_property_gold: 'buy property or gold',
  sign_contract: 'sign a contract',
  start_journey: 'start a journey',
  griha_pravesha: 'do Griha Pravesha',
  upanayana: 'perform Upanayana',
  namakarana: 'hold Namakarana',
  annaprashana: 'hold Annaprashana',
  vidyarambha: 'begin learning',
  start_venture: 'start a new venture',
  marriage_related: 'plan something marriage-related',
  general: 'do what you’re planning',
};

const RANGE_LABELS: Record<string, string> = {
  week: 'This week',
  month: 'This month',
  custom: 'Your dates',
};

const DEPLOYED_GOAL_FALLBACKS: Record<string, string> = {
  griha_pravesha: 'buy_property_gold',
  upanayana: 'general',
  namakarana: 'general',
  annaprashana: 'general',
  vidyarambha: 'start_venture',
};

/**
 * Muhurta — Results (Figma node 31:57).
 *
 * Ranked windows for one stated purpose. Each carries the rule that produced
 * it — "Amrit Kalam overlaps a favourable Choghadiya", "Strong Abhijit
 * muhurta" — rather than a bare score, because those rules are exactly the
 * convention-dependent part: Choghadiya, Abhijit and the sunrise the whole
 * scheme hangs off all have more than one defensible reckoning. Naming the
 * rule is what lets a reader who follows a different tradition see that it is
 * a different tradition, and not a mistake. The place is in the subheading for
 * the same reason: a muhurta is sunrise-relative and does not travel.
 *
 * The closing line — timing supports the intent, the decision and diligence
 * are still the reader's — is the screen's point, not its disclaimer. An
 * auspicious window is not a warranty, and a contract signed in one is still a
 * contract someone has to read.
 */
@Component({
  selector: 'as-muhurta-results',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
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
  protected readonly error = signal<string | null>(null);
  protected readonly searched = signal(false);
  protected readonly note = signal<string | null>(null);
  protected readonly disclaimer = signal('Timing supports your intent — the decision and diligence are still yours.');

  protected readonly heading = computed(() => {
    const goal = this.params().get('goal') ?? 'sign_contract';
    const intent = this.params().get('intent')?.trim();
    if (goal === 'general' && intent) return `Best times for ${intent}`;
    return `Best times to ${GOAL_PHRASES[goal] ?? GOAL_PHRASES['general']}`;
  });

  protected readonly scope = computed(() => {
    const range = this.params().get('range') ?? 'month';
    return `${RANGE_LABELS[range] ?? RANGE_LABELS['month']} · ${this.dateScope()} · ${this.place()}`;
  });

  readonly place = signal('current panchanga place');

  readonly windows = signal<MuhurtaWindow[]>([]);

  constructor() {
    void this.load();
  }

  protected retry(): void {
    void this.load();
  }

  private async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    this.searched.set(false);
    try {
      await this.kundlis.load();
      const activeId = this.kundlis.activeId();
      if (!activeId) {
        this.windows.set([]);
        return;
      }
      const goal = this.params().get('goal') ?? 'sign_contract';
      const dateFrom = this.params().get('date_from') ?? this.isoDate(new Date());
      const dateTo = this.params().get('date_to') ?? this.isoDate(this.addDays(new Date(), 30));
      const place = this.preferences.panchangaPlace();
      const payload = await this.loadMuhurta(activeId, goal, dateFrom, dateTo, place);
      this.place.set(place ? `${place.city}, ${place.nation}` : 'current panchanga place');
      this.note.set(payload.note);
      this.disclaimer.set(payload.disclaimer);
      this.windows.set(this.extractWindows(payload.results));
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.searched.set(true);
      this.loading.set(false);
    }
  }

  private async loadMuhurta(
    activeId: string,
    goal: string,
    dateFrom: string,
    dateTo: string,
    place: { city: string; nation: string } | null,
  ) {
    try {
      return await this.vedic.muhurta(activeId, goal, dateFrom, dateTo, place);
    } catch (error) {
      const fallback = DEPLOYED_GOAL_FALLBACKS[goal];
      const message = (error as Error).message ?? '';
      if (!fallback || !message.toLowerCase().includes('unknown goal')) throw error;
      const payload = await this.vedic.muhurta(activeId, fallback, dateFrom, dateTo, place);
      return {
        ...payload,
        note: payload.note ?? `Using the closest available panchanga rules for ${GOAL_PHRASES[goal] ?? 'this intent'} until the dedicated backend rule is live.`,
      };
    }
  }

  private extractWindows(results: MuhurtaApiWindow[]): MuhurtaWindow[] {
    return results.map((window, index) => ({
        rank: index + 1,
        date: this.dateLabel(window.date),
        quality: window.quality === 'best' ? 'best' : 'good',
        time: `${window.start} – ${window.end}`,
        score: window.score,
        window: window.window,
        supports: window.why.supports,
        against: window.why.against,
        reason: this.reason(window),
      }));
  }

  private reason(window: MuhurtaApiWindow): string {
    const parts = [
      `${window.window} · ${window.score}/100`,
      window.vara ? `${window.vara} vara` : null,
      window.nakshatra ? `${window.nakshatra} nakshatra` : null,
      window.trimmed ? 'trimmed around avoid-windows' : null,
    ].filter(Boolean);
    return `${parts.join(' · ')}.`;
  }

  private dateLabel(value: string): string {
    const date = new Date(`${value}T12:00:00`);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
  }

  private dateScope(): string {
    const from = this.params().get('date_from');
    const to = this.params().get('date_to');
    if (!from || !to) return 'next 30 days';
    if (from === to) return this.shortDate(from);
    return `${this.shortDate(from)} - ${this.shortDate(to)}`;
  }

  private shortDate(value: string): string {
    const date = new Date(`${value}T12:00:00`);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  private addDays(date: Date, days: number): Date {
    const next = new Date(date);
    next.setDate(next.getDate() + days);
    return next;
  }

  private isoDate(date: Date): string {
    return date.toISOString().slice(0, 10);
  }
}
