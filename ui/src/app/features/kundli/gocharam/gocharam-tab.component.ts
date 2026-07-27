import { TitleCasePipe } from '@angular/common';
import { Component, computed, effect, inject, signal } from '@angular/core';
import { Skeleton } from 'primeng/skeleton';

import { KundliStore } from '../../../core/kundli.store';
import {
  GocharaActiveWindow,
  GocharamMatchedRule,
  GocharamPeriod,
  GocharamProfilePayload,
  TransitTimelineEvent,
} from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { SectionCardComponent } from '../../../shared/section-card/section-card.component';

type WorkspaceView = 'summary' | 'transits' | 'timeline';
type ScanRangeDays = 30 | 90 | 365 | 1095;

interface TimelineBar {
  period: GocharamPeriod;
  left: number;
  width: number;
}

interface TimelineTrack {
  key: string;
  rule: string;
  planet: string;
  bars: TimelineBar[];
}

@Component({
  selector: 'app-gocharam-tab',
  imports: [Skeleton, SectionCardComponent, TitleCasePipe],
  templateUrl: './gocharam-tab.component.html',
  styleUrl: './gocharam-tab.component.scss',
})
export class GocharamTabComponent {
  private store = inject(KundliStore);
  private vedic = inject(VedicService);

  protected readonly data = signal<GocharamProfilePayload | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly refreshing = signal(false);
  protected readonly loading = computed(() => !this.data() && !this.error());
  protected readonly workspace = signal<WorkspaceView>('summary');
  protected readonly scanRangeDays = signal<ScanRangeDays>(90);
  protected readonly selectedDate = signal<string | null>(null);
  
  protected readonly ruleId = signal<string | null>(null);

  protected readonly scanOptions: ReadonlyArray<{ days: ScanRangeDays; label: string }> = [
    { days: 30, label: '30 days' },
    { days: 90, label: '90 days' },
    { days: 365, label: '1 year' },
    { days: 1095, label: '3 years' },
  ];
  private requestSequence = 0;
  private requestedProfileId: string | null = null;

  protected readonly activeWindows = computed(() => this.data()?.gochara.timeline.active_windows ?? []);
  
  protected readonly matchedRules = computed(() => this.data()?.gochara.interpretation?.matched_rules ?? []);
  
  protected readonly activeRule = computed<GocharamMatchedRule | null>(() => {
    const rules = this.matchedRules();
    const id = this.ruleId();
    if (id) {
       const found = rules.find((rule) => rule.rule_id === id);
       if (found) return found;
    }
    return rules[0] ?? null;
  });

  protected readonly scanRangeLabel = computed(
    () => this.scanOptions.find((option) => option.days === this.scanRangeDays())?.label ?? '',
  );
  protected readonly viewDate = computed(
    () => this.selectedDate() ?? this.data()?.as_of.slice(0, 10) ?? '',
  );
  protected readonly viewDateLabel = computed(() => this.formatDate(this.viewDate()));
  
  protected readonly timelineBounds = computed(() => {
    const center = this.dayNumber(this.viewDate());
    if (center === null) return null;
    const days = this.scanRangeDays();
    return {
      start: center - days,
      end: center + days,
      startLabel: this.formatDate(this.dateFromDay(center - days)),
      endLabel: this.formatDate(this.dateFromDay(center + days)),
    };
  });
  
  protected readonly nextEvent = computed(
    () =>
      this.data()?.gochara.timeline.next_365_days.find((event) =>
        this.isWithinScan(event.date, 'future'),
      ) ?? null,
  );
  
  protected readonly previousEvent = computed(
    () =>
      this.data()?.gochara.timeline.previous_365_days.find((event) =>
        this.isWithinScan(event.date, 'past'),
      ) ?? null,
  );
  
  protected readonly visiblePeriods = computed(() => {
    const periods = this.data()?.periods ?? [];
    return periods.filter((period) => {
      if (period.status === 'current') return true;
      const date = period.start_date || period.end_date;
      if (!date) return false;
      return this.isWithinScan(date, period.status === 'past' ? 'past' : 'future');
    });
  });
  
  protected readonly timelineTracks = computed<TimelineTrack[]>(() => {
    const bounds = this.timelineBounds();
    if (!bounds) return [];
    const totalDays = Math.max(1, bounds.end - bounds.start);
    const tracks = new Map<string, TimelineTrack>();
    for (const period of this.visiblePeriods()) {
      const start = this.dayNumber(period.start_date);
      const end = this.dayNumber(period.end_date) ?? bounds.end;
      if (start === null || end < bounds.start || start > bounds.end) continue;
      const visibleStart = Math.max(start, bounds.start);
      const visibleEnd = Math.min(Math.max(end, start + 1), bounds.end);
      const key = period.rule_id;
      const track: TimelineTrack = tracks.get(key) ?? {
        key,
        rule: period.rule,
        planet: period.planet,
        bars: [],
      };
      track.bars.push({
        period,
        left: ((visibleStart - bounds.start) / totalDays) * 100,
        width: Math.max(1.2, ((visibleEnd - visibleStart) / totalDays) * 100),
      });
      tracks.set(key, track);
    }
    return [...tracks.values()].sort((a, b) =>
      a.planet.localeCompare(b.planet) || a.rule.localeCompare(b.rule),
    );
  });
  
  protected readonly nearbyEvents = computed(() => {
    const center = this.dayNumber(this.viewDate());
    const timeline = this.data()?.gochara.timeline;
    if (center === null || !timeline) return [];
    return [...timeline.previous_365_days, ...timeline.next_365_days]
      .sort((a, b) => {
        const aDay = this.dayNumber(a.date) ?? center;
        const bDay = this.dayNumber(b.date) ?? center;
        return Math.abs(aDay - center) - Math.abs(bDay - center) || aDay - bDay;
      })
      .slice(0, 6);
  });

  constructor() {
    effect(() => {
      const id = this.store.activeId();
      const scanDays = this.scanRangeDays();
      const selectedDate = this.selectedDate();
      const request = ++this.requestSequence;
      this.error.set(null);
      if (!id) {
        this.data.set(null);
        this.refreshing.set(false);
        this.requestedProfileId = null;
        return;
      }
      if (id !== this.requestedProfileId) {
        this.requestedProfileId = id;
        this.data.set(null);
      } else {
        this.refreshing.set(true);
      }
      this.vedic
        .gocharam(id, scanDays, selectedDate)
        .then((payload) => {
          if (request !== this.requestSequence) return;
          this.data.set(payload);
        })
        .catch((e) => {
          if (request !== this.requestSequence) return;
          this.error.set((e as Error).message);
        })
        .finally(() => {
          if (request === this.requestSequence) this.refreshing.set(false);
        });
    });
  }

  protected toneClass(tone?: string): string {
    if (tone === 'supportive') return 'supportive';
    if (tone === 'challenging' || tone === 'hard' || tone === 'mixed') return 'challenging';
    return 'neutral';
  }

  protected categoryClass(category?: string): string {
    if (category === 'growth' || category === 'auspicious') return 'supportive';
    if (category === 'health_and_obstacles' || category === 'domestic_peace') return 'challenging';
    return 'neutral';
  }

  protected selectWorkspace(view: WorkspaceView): void {
    this.workspace.set(view);
  }

  protected setScanRange(days: ScanRangeDays): void {
    this.scanRangeDays.set(days);
  }

  protected setViewDate(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    if (value) this.selectedDate.set(value);
  }

  protected moveViewDate(days: number): void {
    const current = this.dayNumber(this.viewDate());
    if (current === null) return;
    this.selectedDate.set(this.dateFromDay(current + days));
  }

  protected resetViewDate(): void {
    const now = new Date();
    this.selectedDate.set(
      this.dateFromDay(
        Math.floor(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) / 86_400_000),
      ),
    );
  }

  protected selectTimelineDate(value?: string | null): void {
    if (value) this.selectedDate.set(value);
  }

  private isWithinScan(value: string, direction: 'past' | 'future'): boolean {
    const asOf = this.data()?.as_of;
    if (!asOf) return false;
    const origin = new Date(asOf).getTime();
    const target = new Date(`${value}T12:00:00`).getTime();
    const deltaDays = (target - origin) / 86_400_000;
    return direction === 'future'
      ? deltaDays >= -1 && deltaDays <= this.scanRangeDays()
      : deltaDays <= 1 && deltaDays >= -this.scanRangeDays();
  }

  protected formatDate(value?: string | null): string {
    if (!value) return 'Open';
    return new Intl.DateTimeFormat('en', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(new Date(`${value}T12:00:00`));
  }

  protected formatRange(window: GocharaActiveWindow): string {
    return `${this.formatDate(window.start_date)} -> ${this.formatDate(window.end_date)}`;
  }

  protected eventTrack(event: TransitTimelineEvent): string {
    return `${event.date}-${event.rule || event.title}-${event.transition || event.type}`;
  }

  protected periodTrack(period: GocharamPeriod): string {
    return `${period.status}-${period.rule_id}-${period.start_date}-${period.end_date}`;
  }

  private dayNumber(value?: string | null): number | null {
    if (!value) return null;
    const [year, month, day] = value.slice(0, 10).split('-').map(Number);
    if (!year || !month || !day) return null;
    return Math.floor(Date.UTC(year, month - 1, day) / 86_400_000);
  }

  private dateFromDay(day: number): string {
    return new Date(day * 86_400_000).toISOString().slice(0, 10);
  }
}
