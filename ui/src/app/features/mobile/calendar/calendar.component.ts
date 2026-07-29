import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { CalendarIntelligencePayload } from '../../../core/models';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';

interface CalendarCell {
  date: string;
  day: number;
  inPayload: boolean;
  eventCount: number;
}

@Component({
  selector: 'as-mobile-calendar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
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
      @if (loading()) {
        <section class="mcal-state"><b>Loading calendar</b><p>Checking timing signals for {{ activeName() }}.</p></section>
      } @else if (error()) {
        <section class="mcal-state error" role="alert">
          <b>Calendar could not load</b>
          <p>{{ error() }}</p>
          <button type="button" (click)="reload()">Retry</button>
        </section>
      } @else if (!activeId()) {
        <section class="mcal-state"><b>No active profile</b><p>Select a profile before loading calendar guidance.</p></section>
      } @else if (data(); as calendar) {
        <section class="mcal-grid">
          @for (day of weekdays; track day) { <span class="mcal-weekday">{{ day }}</span> }
          @for (_ of blanks(); track $index) { <span></span> }
          @for (cell of cells(); track cell.date) {
            <a
              [class.mcal-selected]="cell.date === calendar.start_date"
              [class.mcal-event]="cell.eventCount > 0"
              [class.mcal-empty-day]="!cell.inPayload"
              [routerLink]="['/m','calendar','day']"
              [queryParams]="{ date: cell.date }"
            >{{ cell.day }}</a>
          }
        </section>

        <p class="mcal-eyebrow">UPCOMING SIGNALS</p>
        @if (preferences.experienceMode() === 'practitioner') {
          <p class="mcal-eyebrow">{{ calendar.system }} · {{ calendar.timezone }} · {{ calendar.place.city }}</p>
        }
        @for (event of visibleEvents(); track event.date + event.title) {
          <a class="mcal-observance" [routerLink]="['/m','calendar','day']" [queryParams]="{ date: event.date }">
            <span class="mcal-date-tile"><b>{{ dayNumber(event.date) }}</b><small>{{ monthShort(event.date) }}</small></span>
            <span><b>{{ event.title }}</b><small>{{ event.detail }}</small><em>{{ event.category }} · strength {{ event.strength }}</em></span>
          </a>
        } @empty {
          <section class="mcal-state">
            <b>No signals in this month</b>
            <p>The loaded calendar window has no events for {{ monthLabel() }}.</p>
          </section>
        }
      }
    </main>
  `,
  styleUrl: './calendar.component.scss',
})
export class CalendarComponent {
  protected readonly preferences = inject(PreferencesService);
  private readonly store = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  private requestId = 0;

  protected readonly weekdays = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
  protected readonly data = signal<CalendarIntelligencePayload | null>(null);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly visibleMonth = signal<string | null>(null);
  protected readonly activeId = computed(() => this.store.activeId());
  protected readonly activeName = computed(() => this.store.active()?.name ?? 'this profile');

  protected readonly monthStart = computed(() => {
    const month = this.visibleMonth() ?? this.data()?.start_date.slice(0, 7) ?? this.todayMonth();
    return new Date(`${month}-01T12:00:00`);
  });
  protected readonly blanks = computed(() => Array.from({ length: this.monthStart().getDay() }));
  protected readonly cells = computed<CalendarCell[]>(() => {
    const start = this.monthStart();
    const year = start.getFullYear();
    const month = start.getMonth();
    const days = new Date(year, month + 1, 0).getDate();
    const payloadDates = new Set(this.data()?.panchanga_days.map((day) => day.date) ?? []);
    const byDate = this.data()?.by_date ?? {};
    return Array.from({ length: days }, (_, index) => {
      const date = this.isoDate(year, month, index + 1);
      return {
        date,
        day: index + 1,
        inPayload: payloadDates.has(date) || !!byDate[date],
        eventCount: byDate[date]?.length ?? 0,
      };
    });
  });
  protected readonly visibleEvents = computed(() => {
    const month = this.visibleMonth() ?? this.data()?.start_date.slice(0, 7);
    if (!month) return [];
    return [...(this.data()?.events ?? [])]
      .filter((event) => event.date.startsWith(month))
      .sort((a, b) => a.date.localeCompare(b.date) || b.strength - a.strength)
      .slice(0, 8);
  });

  constructor() {
    effect(() => {
      void this.load(this.activeId());
    });
  }

  protected reload(): void {
    void this.load(this.activeId());
  }

  protected shiftMonth(delta: number): void {
    const next = new Date(this.monthStart());
    next.setMonth(next.getMonth() + delta);
    this.visibleMonth.set(`${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, '0')}`);
  }

  protected canGoPrevious(): boolean {
    const first = this.data()?.start_date.slice(0, 7);
    const current = this.visibleMonth() ?? first;
    return !!first && !!current && current > first;
  }

  protected canGoNext(): boolean {
    const last = this.data()?.end_date.slice(0, 7);
    const current = this.visibleMonth() ?? this.data()?.start_date.slice(0, 7);
    return !!last && !!current && current < last;
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

  private async load(id: string | null): Promise<void> {
    const request = ++this.requestId;
    this.error.set(null);
    this.data.set(null);
    if (!id) return;
    this.loading.set(true);
    try {
      const calendar = await this.vedic.calendarIntelligence(id, 45);
      if (request !== this.requestId || this.activeId() !== id) return;
      this.data.set(calendar);
      this.visibleMonth.set(calendar.start_date.slice(0, 7));
    } catch (error) {
      if (request === this.requestId) this.error.set((error as Error).message);
    } finally {
      if (request === this.requestId) this.loading.set(false);
    }
  }

  private isoDate(year: number, month: number, day: number): string {
    return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  }

  private todayMonth(): string {
    const today = new Date();
    return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
  }
}
