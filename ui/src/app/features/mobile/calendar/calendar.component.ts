import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { FestivalService } from '../../../core/festival.service';
import { KundliStore } from '../../../core/kundli.store';
import { FestivalOccurrence } from '../../../core/models';
import { PreferencesService } from '../../../core/preferences.service';
import { FestivalSheetComponent } from './festival-sheet.component';

interface CalendarCell {
  date: string;
  day: number;
  eventCount: number;
}

@Component({
  selector: 'as-mobile-calendar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FestivalSheetComponent, RouterLink],
  template: `
    <header class="mcal-top">
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
          @for (day of weekdays; track day) { <span class="mcal-weekday">{{ day }}</span> }
          @for (_ of blanks(); track $index) { <span></span> }
          @for (cell of cells(); track cell.date) {
            <a
              [class.mcal-selected]="cell.date === todayDate()"
              [class.mcal-event]="cell.eventCount > 0"
              [routerLink]="['/m','calendar','day']"
              [queryParams]="{ date: cell.date }"
            >{{ cell.day }}</a>
          }
        </section>

        <p class="mcal-eyebrow">FESTIVALS</p>
        @if (festivalError()) {
          <section class="mcal-state error"><b>Festivals could not load</b><p>{{ festivalError() }}</p><button type="button" (click)="reload()">Retry</button></section>
        }
        @for (festival of visibleFestivals(); track festival.slug + festival.occurs_on) {
          <button class="mcal-observance festival" type="button" (click)="selectedFestival.set(festival)">
            <span class="mcal-date-tile"><b>{{ dayNumber(festival.occurs_on) }}</b><small>{{ monthShort(festival.occurs_on) }}</small></span>
            <span><b>{{ festival.name }}</b><small>{{ festival.description || festival.prep_guidance || 'Tap for observance details' }}</small><em>{{ festival.regions.join(' · ') }}</em></span>
          </button>
        } @empty {
          @if (festivalLoading()) {
            <section class="mcal-observance mcal-skel-row" role="status" aria-label="Loading festivals">
              <span class="mcal-date-tile"></span><span><i></i><i></i><i></i></span>
            </section>
          } @else if (!festivalError()) {
            <section class="mcal-state"><b>No festivals in this window</b><p>No major Hindu festivals were returned for {{ monthLabel() }}.</p></section>
          }
        }
      }
    </main>
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
  private festivalRequestId = 0;

  protected readonly weekdays = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
  protected readonly festivalLoading = signal(false);
  protected readonly festivalError = signal<string | null>(null);
  protected readonly festivalRows = signal<FestivalOccurrence[]>([]);
  protected readonly selectedFestival = signal<FestivalOccurrence | null>(null);
  protected readonly visibleMonth = signal(this.todayMonth());
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
    return Array.from({ length: days }, (_, index) => {
      const date = this.isoDate(year, month, index + 1);
      return {
        date,
        day: index + 1,
        eventCount: festivalCounts[date] ?? 0,
      };
    });
  });
  protected readonly visibleFestivals = computed(() => {
    const month = this.visibleMonth();
    return this.festivalRows()
      .filter((festival) => festival.occurs_on.startsWith(month))
      .sort((a, b) => a.occurs_on.localeCompare(b.occurs_on) || a.name.localeCompare(b.name))
      .slice(0, 8);
  });

  constructor() {
    effect(() => {
      const profileId = this.activeId();
      this.preferences.panchangaContextKey();
      const regions = this.preferences.festivalRegions();
      const month = this.visibleMonth();
      if (profileId) void this.loadFestivals(`${month}-01`, this.daysInVisibleMonth(), regions);
    });
  }

  protected reload(): void {
    const month = this.visibleMonth();
    void this.loadFestivals(`${month}-01`, this.daysInVisibleMonth(), this.preferences.festivalRegions(), true);
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
    return this.visibleMonth() > this.todayMonth();
  }

  protected canGoNext(): boolean {
    return this.visibleMonth() < this.monthOffset(this.todayMonth(), 12);
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
    const place = this.preferences.panchangaPlace();
    const profile = this.store.active();
    const city = place?.city || profile?.birth_city;
    const nation = place?.nation || profile?.birth_nation || 'IN';
    this.festivalRows.set([]);
    if (!city) {
      this.festivalLoading.set(false);
      this.festivalError.set('Set a Panchanga place to load local festivals.');
      return;
    }
    const cached = forceRefresh ? null : this.festivals.cachedUpcoming(city, nation, fromDate, days, regions);
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
        ? await this.festivals.refreshUpcoming(city, nation, fromDate, days, regions)
        : await this.festivals.upcoming(city, nation, fromDate, days, regions);
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
