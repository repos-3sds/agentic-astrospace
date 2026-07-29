import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { FestivalService } from '../../../core/festival.service';
import { KundliStore } from '../../../core/kundli.store';
import { CalendarEvent, CalendarIntelligencePayload, FestivalOccurrence } from '../../../core/models';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { FestivalSheetComponent } from './festival-sheet.component';

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
      @if (loading()) {
        <section class="mcal-grid mcal-skeleton" role="status" aria-label="Loading calendar">
          @for (day of weekdays; track day) { <span class="mcal-weekday">{{ day }}</span> }
          @for (_ of skeletonDays; track $index) { <span class="mcal-skel-day"></span> }
        </section>
        <p class="mcal-eyebrow">UPCOMING SIGNALS</p>
        @for (_ of [1, 2, 3]; track _) {
          <section class="mcal-observance mcal-skel-row">
            <span class="mcal-date-tile"></span>
            <span><i></i><i></i><i></i></span>
          </section>
        }
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

        <p class="mcal-eyebrow">FESTIVALS</p>
        @if (festivalError()) {
          <section class="mcal-state error"><b>Festivals could not load</b><p>{{ festivalError() }}</p></section>
        }
        @for (festival of visibleFestivals(); track festival.slug + festival.occurs_on) {
          <button class="mcal-observance festival" type="button" (click)="selectedFestival.set(festival)">
            <span class="mcal-date-tile"><b>{{ dayNumber(festival.occurs_on) }}</b><small>{{ monthShort(festival.occurs_on) }}</small></span>
            <span><b>{{ festival.name }}</b><small>{{ festival.description || festival.prep_guidance || 'Tap for observance details' }}</small><em>{{ festival.regions.join(' · ') }}</em></span>
          </button>
        } @empty {
          @if (!festivalLoading() && !festivalError()) {
            <section class="mcal-state"><b>No festivals in this window</b><p>No major Hindu festivals were returned for {{ monthLabel() }}.</p></section>
          }
        }

        <p class="mcal-eyebrow">PERSONAL SIGNALS</p>
        @if (preferences.experienceMode() === 'practitioner') {
          <p class="mcal-eyebrow">{{ calendar.system }} · {{ calendar.timezone }} · {{ calendar.place.city }}</p>
        }
        @for (event of visibleSignals(); track event.date + event.title) {
          <a class="mcal-observance" [routerLink]="['/m','calendar','day']" [queryParams]="{ date: event.date }">
            <span class="mcal-date-tile"><b>{{ dayNumber(event.date) }}</b><small>{{ monthShort(event.date) }}</small></span>
            <span><b>{{ event.title }}</b><small>{{ signalSummary(event) }}</small><em>{{ event.category }}</em></span>
          </a>
        } @empty {
          <section class="mcal-state">
            <b>No personal signals in this month</b>
            <p>The loaded calendar window has no profile-specific timing events.</p>
          </section>
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
  private readonly vedic = inject(VedicService);
  private readonly festivals = inject(FestivalService);
  private requestId = 0;

  protected readonly weekdays = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
  protected readonly skeletonDays = Array.from({ length: 35 });
  protected readonly data = signal<CalendarIntelligencePayload | null>(null);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly festivalLoading = signal(false);
  protected readonly festivalError = signal<string | null>(null);
  protected readonly festivalRows = signal<FestivalOccurrence[]>([]);
  protected readonly selectedFestival = signal<FestivalOccurrence | null>(null);
  protected readonly visibleMonth = signal<string | null>(null);
  protected readonly activeId = computed(() => this.store.activeId());
  protected readonly activeName = computed(() => this.store.active()?.name ?? 'this profile');
  private renderedProfileId: string | null = null;

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
  protected readonly visibleSignals = computed(() => {
    const month = this.visibleMonth() ?? this.data()?.start_date.slice(0, 7);
    if (!month) return [];
    return [...(this.data()?.events ?? [])]
      .filter((event) => event.date.startsWith(month))
      .sort((a, b) => a.date.localeCompare(b.date) || b.strength - a.strength)
      .slice(0, 4);
  });
  protected readonly visibleFestivals = computed(() => {
    const month = this.visibleMonth() ?? this.data()?.start_date.slice(0, 7);
    if (!month) return [];
    return this.festivalRows()
      .filter((festival) => festival.occurs_on.startsWith(month))
      .sort((a, b) => a.occurs_on.localeCompare(b.occurs_on) || a.name.localeCompare(b.name))
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
    if (!id) {
      this.data.set(null);
      this.renderedProfileId = null;
      this.loading.set(false);
      return;
    }
    const cached = this.vedic.cachedCalendarIntelligence(id, 45);
    if (cached) {
      this.data.set(cached);
      this.visibleMonth.set(cached.start_date.slice(0, 7));
      this.renderedProfileId = id;
      this.loading.set(false);
      void this.loadFestivals(cached.start_date, 60);
      return;
    }
    if (this.renderedProfileId !== id) {
      this.data.set(null);
      this.loading.set(true);
    }
    try {
      const calendar = await withTimeout(
        this.vedic.calendarIntelligence(id, 45),
        15000,
        'Calendar is taking longer than expected. Check your connection and retry.',
      );
      if (request !== this.requestId || this.activeId() !== id) return;
      this.data.set(calendar);
      this.renderedProfileId = id;
      this.visibleMonth.set(calendar.start_date.slice(0, 7));
      void this.loadFestivals(calendar.start_date, 60);
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

  private async loadFestivals(fromDate: string, days: number): Promise<void> {
    const place = this.preferences.panchangaPlace();
    const profile = this.store.active();
    const city = place?.city || profile?.birth_city;
    const nation = place?.nation || profile?.birth_nation || 'IN';
    if (!city) return;
    this.festivalLoading.set(true);
    this.festivalError.set(null);
    try {
      const payload = await this.festivals.upcoming(city, nation, fromDate, days);
      this.festivalRows.set(payload.festivals);
    } catch (error) {
      this.festivalError.set((error as Error).message);
    } finally {
      this.festivalLoading.set(false);
    }
  }

  protected signalSummary(event: CalendarEvent): string {
    if (this.preferences.experienceMode() === 'practitioner') return event.detail;
    return event.tone === 'challenging' || event.tone === 'hard'
      ? 'Use care around this timing.'
      : event.tone === 'supportive'
        ? 'Supportive timing marker.'
        : 'Timing marker from your profile.';
  }
}

function withTimeout<T>(promise: Promise<T>, timeoutMs: number, message: string): Promise<T> {
  let timeout: ReturnType<typeof setTimeout> | undefined;
  const timeoutPromise = new Promise<never>((_, reject) => {
    timeout = setTimeout(() => reject(new Error(message)), timeoutMs);
  });
  return Promise.race([promise, timeoutPromise]).finally(() => {
    if (timeout) clearTimeout(timeout);
  });
}
