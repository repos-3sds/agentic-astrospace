import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { FestivalService, festivalPlace, festivalRegionsLabel } from '../../../core/festival.service';
import { KundliStore } from '../../../core/kundli.store';
import { DayQuality, FestivalOccurrence, VratDay } from '../../../core/models';
import { PanchangaService } from '../../../core/panchanga.service';
import { PreferencesService } from '../../../core/preferences.service';
import { PullRefreshService } from '../../../core/pull-refresh.service';
import { FestivalSheetComponent } from './festival-sheet.component';
import { CalendarDayComponent } from './calendar-day.component';
import { tabletLayout, wideLayout } from '../../../core/screen-size';
import { StickyBarDirective } from '../shared/sticky-bar.directive';

interface CalendarCell {
  date: string;
  day: number;
  eventCount: number;
  quality: DayQuality['quality'] | null;
}

/** One row of the month's list: a festival, or a vrat day with its rule. */
type MonthRow =
  | { type: 'festival'; date: string; festival: FestivalOccurrence }
  | { type: 'vrat'; date: string; vrat: VratDay };

const QUALITY_WORDS: Record<DayQuality['quality'], string> = {
  good: 'a good day for you',
  mixed: 'a mixed day',
  care: 'a day to take care',
};

/** A named festival already covers the vrat (Vaikuntha Ekadashi, Kartika Purnima). */
function coveredBy(vrat: VratDay, festivals: FestivalOccurrence[]): boolean {
  const word = vrat.kind === 'pradosham' ? 'pradosh' : vrat.kind;
  return festivals.some((f) => f.occurs_on === vrat.date && f.name.toLowerCase().includes(word));
}

@Component({
  selector: 'as-mobile-calendar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [StickyBarDirective, FestivalSheetComponent, RouterLink, CalendarDayComponent],
  template: `
    <div class="mcal-month">
    <header class="mcal-top" asStickyBar>
      <h1>Calendar</h1>
      <div>
        <button type="button" aria-label="Previous month" [disabled]="!canGoPrevious()" (click)="shiftMonth(-1)"><img src="mobile/back.svg" alt="" /></button>
        <b>{{ monthLabel() }}</b>
        <button type="button" class="mcal-next" aria-label="Next month" [disabled]="!canGoNext()" (click)="shiftMonth(1)"><img src="mobile/back.svg" alt="" /></button>
      </div>
    </header>

    <main class="mcal-body">
      @if (!activeId()) {
        <section class="mcal-state"><b>No active profile</b><p>Select a profile before loading calendar guidance.</p></section>
      } @else {
        <section
          class="mcal-grid"
          (touchstart)="startMonthSwipe($event)"
          (touchend)="finishMonthSwipe($event)"
        >
          @for (day of weekdays; track $index) { <span class="mcal-weekday">{{ day }}</span> }
          @for (_ of blanks(); track $index) { <span></span> }
          @for (cell of cells(); track cell.date) {
            <a
              [class.mcal-selected]="cell.date === selectedDate()"
              [class.mcal-today]="cell.date === todayDate()"
              [class.mcal-event]="cell.eventCount > 0"
              [class.mcal-q-good]="cell.quality === 'good'"
              [class.mcal-q-care]="cell.quality === 'care'"
              [routerLink]="tablet() ? ['/m','calendar'] : ['/m','calendar','day']"
              [queryParams]="{ date: cell.date }"
              [replaceUrl]="tablet()"
              [attr.aria-label]="cellLabel(cell.date, cell.eventCount, cell.quality)"
              [attr.aria-current]="cell.date === todayDate() ? 'date' : null"
            >{{ cell.day }}</a>
          }
        </section>
        <div class="mcal-legend">
          @if (qualityByDate().size) {
            <span><i class="good"></i>Good day for {{ forWhom() }}</span>
            <span><i class="care"></i>Take care</span>
          }
          <span><i class="event"></i>Festival or vrat</span>
        </div>
        @if (qualityNote(); as note) {
          <details class="mcal-about"><summary>What the colours mean</summary><p>{{ note }}</p></details>
        }
        @if (tablet() && !wide()) {
          <section class="mcal-day-pane" aria-label="Chosen day"><as-calendar-day [embedded]="true" /></section>
        }

        <p class="mcal-eyebrow">FESTIVALS AND VRAT DAYS</p>
        @if (festivalError()) {
          <section class="mcal-state error"><b>Festivals could not load</b><p>{{ festivalError() }}</p><button type="button" (click)="reload()">Retry</button></section>
        }
        @for (row of monthRows(); track row.type + row.date + (row.type === 'festival' ? row.festival.slug : row.vrat.kind)) {
          @if (row.type === 'festival') {
            <button class="mcal-observance m-pressable festival" type="button" (click)="selectedFestival.set(row.festival)">
              <span class="mcal-date-tile"><b>{{ dayNumber(row.date) }}</b><small>{{ monthShort(row.date) }}</small></span>
              <span><b>{{ row.festival.name }}</b><small>{{ row.festival.description || row.festival.prep_guidance || 'Tap for observance details' }}</small><em>{{ regionsLabel(row.festival.regions) }}@if (row.festival.is_convention_dependent) { · Varies by tradition }</em></span>
            </button>
          } @else {
            <button class="mcal-observance m-pressable vrat" type="button" (click)="selectedFestival.set(vratAsFestival(row.vrat))">
              <span class="mcal-date-tile"><b>{{ dayNumber(row.date) }}</b><small>{{ monthShort(row.date) }}</small></span>
              <span><b>{{ row.vrat.name }}</b><small>{{ vratLine(row.vrat) }}</small><em>Varies by tradition</em></span>
            </button>
          }
        } @empty {
          @if (festivalLoading()) {
            <section class="mcal-observance mcal-skel-row" role="status" aria-label="Loading festivals">
              <span class="mcal-date-tile"></span><span><i></i><i></i><i></i></span>
            </section>
          } @else if (!festivalError()) {
            @if (visibleMonth() === todayDate().slice(0, 7)) {
              <section class="mcal-state"><b>Nothing more this month</b><p>The rest of {{ monthLabel() }} has no festivals or vrat days. Next month's are one tap ahead.</p></section>
            } @else {
              <section class="mcal-state"><b>Nothing in this month</b><p>No festivals or vrat days were returned for {{ monthLabel() }}.</p></section>
            }
          }
        }
        @if (vratRules().length) {
          <details class="mcal-about">
            <summary>How these dates are worked out</summary>
            @for (rule of vratRules(); track rule.kind) { <p><b>{{ rule.label }}.</b> {{ rule.note }}</p> }
          </details>
        }
      }
    </main>
    </div>
    @if (wide() && activeId()) {
      <section class="mcal-day-pane" aria-label="Chosen day"><as-calendar-day [embedded]="true" /></section>
    }
    @if (selectedFestival(); as festival) {
      <as-festival-sheet [festival]="festival" (dismissed)="selectedFestival.set(null)" />
    }
  `,
  styleUrl: './calendar.component.scss',
})
export class CalendarComponent {
  protected readonly preferences = inject(PreferencesService);
  private readonly store = inject(KundliStore);
  private readonly festivals = inject(FestivalService);
  private readonly panchanga = inject(PanchangaService);
  private festivalRequestId = 0;
  private extrasRequestId = 0;

  protected readonly weekdays = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
  protected readonly festivalLoading = signal(false);
  protected readonly festivalError = signal<string | null>(null);
  protected readonly festivalRows = signal<FestivalOccurrence[]>([]);
  protected readonly selectedFestival = signal<FestivalOccurrence | null>(null);
  protected readonly vratRows = signal<VratDay[]>([]);
  protected readonly qualityByDate = signal<Map<string, DayQuality['quality']>>(new Map());
  protected readonly qualityNote = signal<string | null>(null);
  protected readonly forWhom = computed(() => {
    const active = this.store.active();
    return !active || (active.relation || '').toLowerCase() === 'self' ? 'you' : active.name.split(' ')[0];
  });
  protected readonly visibleMonth = signal(this.todayMonth());
  /**
   * Tablets show the chosen day beside the month (below it in portrait), so a
   * tap picks a date here instead of opening the day screen. Phones mark today.
   */
  protected readonly tablet = tabletLayout();
  protected readonly wide = wideLayout();
  private readonly pickedDate = signal<string | null>(null);
  protected readonly selectedDate = computed(() => (this.tablet() && this.pickedDate()) || this.todayDate());
  protected readonly activeId = computed(() => this.store.activeId());
  private monthSwipeStart: { x: number; y: number } | null = null;

  protected readonly monthStart = computed(() => {
    return new Date(`${this.visibleMonth()}-01T12:00:00`);
  });
  protected readonly blanks = computed(() => Array.from({ length: this.monthStart().getDay() }));
  protected readonly cells = computed<CalendarCell[]>(() => {
    const start = this.monthStart();
    const year = start.getFullYear();
    const month = start.getMonth();
    const days = new Date(year, month + 1, 0).getDate();
    const festivalCounts = this.festivalRows().reduce<Record<string, number>>((counts, festival) => {
      counts[festival.occurs_on] = (counts[festival.occurs_on] ?? 0) + 1;
      return counts;
    }, {});
    for (const vrat of this.vratRows()) festivalCounts[vrat.date] = (festivalCounts[vrat.date] ?? 0) + 1;
    const quality = this.qualityByDate();
    return Array.from({ length: days }, (_, index) => {
      const date = this.isoDate(year, month, index + 1);
      return {
        date,
        day: index + 1,
        eventCount: festivalCounts[date] ?? 0,
        quality: quality.get(date) ?? null,
      };
    });
  });
  /** Each vrat kind's rule once, so the dates ship with the convention used. */
  protected readonly vratRules = computed(() => {
    const seen = new Map<string, { kind: string; label: string; note: string }>();
    for (const row of this.monthRows()) {
      if (row.type !== 'vrat' || seen.has(row.vrat.kind)) continue;
      const label = row.vrat.kind === 'purnima' || row.vrat.kind === 'amavasya' ? 'Purnima and Amavasya'
        : row.vrat.kind === 'ekadashi' ? 'Ekadashi' : 'Pradosham';
      if ([...seen.values()].some((rule) => rule.label === label)) continue;
      seen.set(row.vrat.kind, { kind: row.vrat.kind, label, note: row.vrat.observance_note });
    }
    return [...seen.values()];
  });

  /**
   * Every festival and vrat day of the month, in date order; no cap (U7).
   * In the current month, days already gone drop off the list (Hawk,
   * 2026-10-29): the list reads as what is coming. The grid still marks
   * them, and an earlier month browsed on purpose still lists everything.
   */
  protected readonly monthRows = computed<MonthRow[]>(() => {
    const month = this.visibleMonth();
    const today = this.todayDate();
    const from = month === today.slice(0, 7) ? today : '';
    const festivals = this.festivalRows().filter((festival) => festival.occurs_on.startsWith(month) && festival.occurs_on >= from);
    const rows: MonthRow[] = [
      ...festivals.map((festival) => ({ type: 'festival' as const, date: festival.occurs_on, festival })),
      ...this.vratRows()
        .filter((vrat) => vrat.date.startsWith(month) && vrat.date >= from && !coveredBy(vrat, festivals))
        .map((vrat) => ({ type: 'vrat' as const, date: vrat.date, vrat })),
    ];
    const name = (row: MonthRow) => (row.type === 'festival' ? row.festival.name : row.vrat.name);
    return rows.sort((a, b) => a.date.localeCompare(b.date) || name(a).localeCompare(name(b)));
  });

  constructor() {
    inject(DestroyRef).onDestroy(inject(PullRefreshService).register('/m/calendar', () => this.pullRefresh()));
    inject(ActivatedRoute).queryParamMap
      .pipe(takeUntilDestroyed())
      .subscribe((params) => {
        const date = params.get('date');
        this.pickedDate.set(date && /^\d{4}-\d{2}-\d{2}$/.test(date) ? date : null);
        if (date && this.tablet() && /^\d{4}-\d{2}$/.test(date.slice(0, 7))) this.visibleMonth.set(date.slice(0, 7));
      });
    effect(() => {
      const profileId = this.activeId();
      this.preferences.panchangaContextKey();
      const regions = this.preferences.festivalRegions();
      const month = this.visibleMonth();
      if (profileId) void this.loadFestivals(`${month}-01`, this.daysInVisibleMonth(), regions);
    });
    effect(() => {
      const profileId = this.activeId();
      this.preferences.panchangaContextKey();
      const month = this.visibleMonth();
      if (profileId) void this.loadMonthExtras(profileId, `${month}-01`, this.daysInVisibleMonth());
    });
  }

  protected reload(): void {
    const month = this.visibleMonth();
    void this.loadFestivals(`${month}-01`, this.daysInVisibleMonth(), this.preferences.festivalRegions(), true);
  }

  /** Pulled down: the visible month's festivals past the cache, and its day marks. */
  private pullRefresh(): Promise<unknown> {
    const month = this.visibleMonth();
    const from = `${month}-01`;
    const days = this.daysInVisibleMonth();
    const profileId = this.activeId();
    return Promise.all([
      this.loadFestivals(from, days, this.preferences.festivalRegions(), true),
      profileId ? this.loadMonthExtras(profileId, from, days) : null,
    ]);
  }

  protected shiftMonth(delta: number): void {
    const next = new Date(this.monthStart());
    next.setMonth(next.getMonth() + delta);
    this.visibleMonth.set(`${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, '0')}`);
  }

  protected startMonthSwipe(event: TouchEvent): void {
    const touch = event.changedTouches.item(0);
    if (!touch) return;
    this.monthSwipeStart = { x: touch.clientX, y: touch.clientY };
  }

  protected finishMonthSwipe(event: TouchEvent): void {
    const start = this.monthSwipeStart;
    const touch = event.changedTouches.item(0);
    this.monthSwipeStart = null;
    if (!start || !touch) return;

    const deltaX = touch.clientX - start.x;
    const deltaY = touch.clientY - start.y;
    const isHorizontalSwipe = Math.abs(deltaX) >= 56 && Math.abs(deltaX) > Math.abs(deltaY) * 1.35;
    if (!isHorizontalSwipe) return;

    if (deltaX < 0 && this.canGoNext()) {
      this.shiftMonth(1);
    } else if (deltaX > 0 && this.canGoPrevious()) {
      this.shiftMonth(-1);
    }
  }

  protected canGoPrevious(): boolean {
    return this.visibleMonth() > this.monthOffset(this.todayMonth(), -12);
  }

  protected canGoNext(): boolean {
    return this.visibleMonth() < this.monthOffset(this.todayMonth(), 12);
  }

  protected readonly regionsLabel = festivalRegionsLabel;

  /** A screen reader heard only "17"; say the date and whether anything falls on it. */
  protected cellLabel(date: string, eventCount: number, quality: DayQuality['quality'] | null = null): string {
    const [y, m, d] = date.split('-').map(Number);
    const label = new Date(y, m - 1, d).toLocaleDateString('en-US', { weekday: 'long', day: 'numeric', month: 'long' });
    const today = date === this.todayDate() ? ', today' : '';
    const kind = quality ? `, ${QUALITY_WORDS[quality]}` : '';
    const events = eventCount ? `, ${eventCount} ${eventCount === 1 ? 'observance' : 'observances'}` : '';
    return `${label}${today}${kind}${events}`;
  }

  /** A vrat day opens the same sheet as a festival, with its own steps and rule. */
  protected vratAsFestival(vrat: VratDay): FestivalOccurrence {
    return {
      slug: `vrat-${vrat.kind}-${vrat.paksha.toLowerCase()}`,
      name: vrat.name,
      regions: ['pan-india'],
      description: this.vratLine(vrat),
      prep_guidance: null,
      occurs_on: vrat.date,
      observance_note: vrat.observance_note,
      is_convention_dependent: vrat.is_convention_dependent,
      guidance: vrat.guidance ?? null,
    };
  }

  protected vratLine(vrat: VratDay): string {
    switch (vrat.kind) {
      case 'ekadashi': return vrat.paksha === 'Shukla' ? 'Fast of the waxing moon\u2019s 11th day' : 'Fast of the waning moon\u2019s 11th day';
      case 'purnima': return 'Full moon day';
      case 'amavasya': return 'New moon day';
      default: return 'Evening worship of Shiva on the 13th day';
    }
  }

  /** Vrat days and the person's day quality: extras, so a failure leaves the festivals alone. */
  private async loadMonthExtras(profileId: string, fromDate: string, days: number): Promise<void> {
    const requestId = ++this.extrasRequestId;
    this.vratRows.set([]);
    this.qualityByDate.set(new Map());
    this.qualityNote.set(null);
    const place = festivalPlace(this.preferences, this.store.owner() ?? this.store.active());
    const [vrats, month] = await Promise.allSettled([
      place ? this.festivals.vratDays(place, fromDate, days) : Promise.reject(new Error('no place')),
      this.panchanga.month(profileId, fromDate, days),
    ]);
    if (requestId !== this.extrasRequestId) return;
    if (vrats.status === 'fulfilled') this.vratRows.set(vrats.value.days);
    if (month.status === 'fulfilled') {
      this.qualityByDate.set(new Map(month.value.days.map((day) => [day.date, day.quality])));
      this.qualityNote.set(month.value.note);
    }
  }

  protected monthLabel(): string {
    return new Intl.DateTimeFormat('en', { month: 'long', year: 'numeric' }).format(this.monthStart());
  }

  protected dayNumber(date: string): number {
    return Number(date.slice(8, 10));
  }

  protected monthShort(date: string): string {
    return new Intl.DateTimeFormat('en', { month: 'short' }).format(new Date(`${date}T12:00:00`));
  }

  private isoDate(year: number, month: number, day: number): string {
    return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  }

  private todayMonth(): string {
    const today = new Date();
    return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
  }

  protected todayDate(): string {
    const today = new Date();
    return this.isoDate(today.getFullYear(), today.getMonth(), today.getDate());
  }

  private async loadFestivals(
    fromDate: string,
    days: number,
    regions = this.preferences.festivalRegions(),
    forceRefresh = false,
  ): Promise<void> {
    const requestId = ++this.festivalRequestId;
    const place = festivalPlace(this.preferences, this.store.owner() ?? this.store.active());
    this.festivalRows.set([]);
    if (!place) {
      this.festivalLoading.set(false);
      this.festivalError.set('Set a Panchanga place to load local festivals.');
      return;
    }
    const cached = forceRefresh ? null : this.festivals.cachedUpcoming(place, fromDate, days, regions);
    if (cached) {
      if (requestId !== this.festivalRequestId) return;
      this.festivalRows.set(cached.festivals);
      this.festivalLoading.set(false);
      this.festivalError.set(null);
      return;
    }
    this.festivalLoading.set(true);
    this.festivalError.set(null);
    try {
      const payload = forceRefresh
        ? await this.festivals.refreshUpcoming(place, fromDate, days, regions)
        : await this.festivals.upcoming(place, fromDate, days, regions);
      if (requestId !== this.festivalRequestId) return;
      this.festivalRows.set(payload.festivals);
    } catch (error) {
      if (requestId !== this.festivalRequestId) return;
      this.festivalError.set((error as Error).message);
    } finally {
      if (requestId === this.festivalRequestId) this.festivalLoading.set(false);
    }
  }

  private daysInVisibleMonth(): number {
    const start = this.monthStart();
    return new Date(start.getFullYear(), start.getMonth() + 1, 0).getDate();
  }

  private monthOffset(month: string, delta: number): string {
    const value = new Date(`${month}-01T12:00:00`);
    value.setMonth(value.getMonth() + delta);
    return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}`;
  }
}
