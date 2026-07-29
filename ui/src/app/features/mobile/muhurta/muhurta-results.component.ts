import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { KundliStore } from '../../../core/kundli.store';
import { CalendarDaySummary, PanchangaWindow } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';

/** How strongly a window is endorsed. Two levels, not a score. */
export type WindowQuality = 'best' | 'good';

export interface MuhurtaWindow {
  rank: number;
  date: string;
  quality: WindowQuality;
  time: string;
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
  property: 'buy property or gold',
  contract: 'sign a contract',
  journey: 'start a journey',
  venture: 'start a new venture',
  marriage: 'plan something marriage-related',
  other: 'do what you’re planning',
};

const RANGE_LABELS: Record<string, string> = {
  week: 'This week',
  month: 'This month',
  custom: 'Your dates',
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
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly searched = signal(false);

  protected readonly heading = computed(() => {
    const goal = this.params().get('goal') ?? 'contract';
    return `Best times to ${GOAL_PHRASES[goal] ?? GOAL_PHRASES['other']}`;
  });

  protected readonly scope = computed(() => {
    const range = this.params().get('range') ?? 'month';
    return `${RANGE_LABELS[range] ?? RANGE_LABELS['month']} · ${this.place()}`;
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
      const range = this.params().get('range') ?? 'month';
      const days = range === 'week' ? 7 : 31;
      const payload = await this.vedic.calendarIntelligence(activeId, days);
      this.place.set(`${payload.place.city}, ${payload.place.nation}`);
      this.windows.set(this.extractWindows(payload.panchanga_days).slice(0, 5));
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.searched.set(true);
      this.loading.set(false);
    }
  }

  private extractWindows(days: CalendarDaySummary[]): MuhurtaWindow[] {
    return days
      .flatMap((day) => day.windows.auspicious.map((window) => ({ day, window, score: this.score(day, window) })))
      .sort((a, b) => b.score - a.score || a.window.start_iso.localeCompare(b.window.start_iso))
      .map(({ day, window, score }, index) => ({
        rank: index + 1,
        date: this.dateLabel(day.date),
        quality: score >= 3 ? 'best' : 'good',
        time: `${window.start} – ${window.end}`,
        reason: this.reason(day, window),
      }));
  }

  private score(day: CalendarDaySummary, window: PanchangaWindow): number {
    return (day.tarabala.favourable ? 1 : 0)
      + (day.chandrabala.favourable && !day.chandrabala.chandrashtama ? 1 : 0)
      + (window.name.toLowerCase().includes('amrit') || window.name.toLowerCase().includes('abhijit') ? 1 : 0)
      - day.inauspicious_count;
  }

  private reason(day: CalendarDaySummary, window: PanchangaWindow): string {
    return [
      `${window.name} returned by the panchanga calculation`,
      day.tarabala.favourable ? `${day.tarabala.tara} tarabala is favourable` : `${day.tarabala.tara} tarabala needs care`,
      day.chandrabala.favourable ? 'chandrabala is supportive' : 'chandrabala is not supportive',
      day.inauspicious_count ? `${day.inauspicious_count} inauspicious window(s) also present that day` : 'no inauspicious window was returned for that day',
    ].join('; ') + '.';
  }

  private dateLabel(value: string): string {
    const date = new Date(`${value}T12:00:00`);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
  }
}
