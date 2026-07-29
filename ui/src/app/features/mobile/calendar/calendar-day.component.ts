import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { FestivalService } from '../../../core/festival.service';
import { KundliStore } from '../../../core/kundli.store';
import { CalendarDaySummary, CalendarEvent, CalendarIntelligencePayload, FestivalOccurrence, PanchangaWindow } from '../../../core/models';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { FestivalSheetComponent } from './festival-sheet.component';
import { MobileSymbol, nakshatraSymbol, tithiSymbol } from '../symbols/mobile-symbols';

@Component({
  selector: 'as-calendar-day',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FestivalSheetComponent, RouterLink],
  template: `
    <a class="mcald-back" [routerLink]="['/m','calendar']"><img src="mobile/back.svg" alt="" /><span>Calendar</span></a>
    <main class="mcald-body">
      @if (loading()) {
        <section class="mcald-state"><b>Loading day</b><p>Checking timing signals for {{ activeName() }}.</p></section>
      } @else if (error()) {
        <section class="mcald-state error" role="alert">
          <b>Day could not load</b>
          <p>{{ error() }}</p>
          <button type="button" (click)="reload()">Retry</button>
        </section>
      } @else if (!activeId()) {
        <section class="mcald-state"><b>No active profile</b><p>Select a profile before opening a calendar day.</p></section>
      } @else if (data(); as calendar) {
        <header><h1>{{ dateLabel(selectedDate()) }}</h1><p>{{ daySubhead() }}</p></header>

        @if (day(); as summary) {
          <section class="mcald-quality" [class.bad]="!summary.tarabala.favourable || !summary.chandrabala.favourable">
            <span><img src="mobile/cancellation-check.svg" alt="" /></span>
            <div><b>{{ qualityLabel(summary) }}</b><small>{{ qualityDetail(summary) }}</small></div>
          </section>

          <p class="mcald-title accent">DAY TIMELINE</p>
          <section class="mcald-list">
            @for (row of windows(summary); track row.name + row.start_iso) {
              <div [class.bad]="row.tone === 'bad'"><i></i><span><b>{{ row.name }}</b><small>{{ row.start }} - {{ row.end }}</small></span><em>{{ row.tone === 'bad' ? 'AVOID' : 'GOOD' }}</em></div>
            } @empty {
              <p>No timing windows were returned for this day.</p>
            }
          </section>

          @if (preferences.experienceMode() === 'practitioner') {
            <p class="mcald-title">PANCHANGA DETAIL</p>
            <section class="mcald-stack">
              <div class="mcald-symbol-row">
                <span class="mcald-symbol" data-kind="tithi" aria-hidden="true">{{ symbolForTithi(summary.tithi).glyph }}</span>
                <span><small>TITHI</small><b>{{ summary.tithi }}</b></span>
              </div>
              <div class="mcald-symbol-row">
                <span class="mcald-symbol" data-kind="nakshatra" aria-hidden="true">{{ symbolForNakshatra(summary.nakshatra).glyph }}</span>
                <span><small>NAKSHATRA</small><b>{{ summary.nakshatra }}</b></span>
              </div>
              <div><small>MOON RASHI</small><b>{{ summary.moon_rashi }}</b></div>
              <div><small>PLACE</small><b>{{ calendar.place.city }} · {{ calendar.timezone }}</b></div>
            </section>
          }
        } @else {
          <section class="mcald-state">
            <b>No panchanga summary returned</b>
            <p>This date is outside the loaded calendar-intelligence window.</p>
          </section>
        }

        <p class="mcald-title accent">FESTIVALS</p>
        <section class="mcald-stack">
          @for (festival of dayFestivals(); track festival.slug + festival.occurs_on) {
            <button class="festival-row" type="button" (click)="selectedFestival.set(festival)">
              <small>{{ festival.regions.join(' · ') }}</small>
              <b>{{ festival.name }}</b>
              <p>{{ festival.description || festival.prep_guidance || 'Tap for observance details.' }}</p>
            </button>
          } @empty {
            <div><small>NONE</small><b>No major festival returned for this date</b></div>
          }
        </section>

        <p class="mcald-title">RELATED SIGNALS</p>
        <section class="mcald-stack">
          @for (event of events(); track event.title + event.date) {
            <div><small>{{ event.category }}</small><b>{{ event.title }}</b><p>{{ signalSummary(event) }}</p></div>
          } @empty {
            <div><small>NONE</small><b>No profile-specific events returned</b></div>
          }
        </section>

        <p class="mcald-title">ACTIVE PERIOD STACK</p>
        <section class="mcald-stack">
          @for (row of periods(calendar); track row[0]) { <div><small>{{ row[0] }}</small><b>{{ row[1] }}</b></div> }
        </section>
      }
    </main>
    @if (selectedFestival(); as festival) {
      <as-festival-sheet [festival]="festival" (dismissed)="selectedFestival.set(null)" />
    }
  `,
  styleUrl: './calendar-day.component.scss',
})
export class CalendarDayComponent {
  protected readonly preferences = inject(PreferencesService);
  private readonly store = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  private readonly festivals = inject(FestivalService);
  private readonly route = inject(ActivatedRoute);
  private requestId = 0;

  protected readonly data = signal<CalendarIntelligencePayload | null>(null);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly festivalRows = signal<FestivalOccurrence[]>([]);
  protected readonly selectedFestival = signal<FestivalOccurrence | null>(null);
  protected readonly selectedDate = signal(this.route.snapshot.queryParamMap.get('date') ?? '');
  protected readonly activeId = computed(() => this.store.activeId());
  protected readonly activeName = computed(() => this.store.active()?.name ?? 'this profile');
  protected readonly day = computed<CalendarDaySummary | null>(() => {
    const date = this.selectedDate() || this.data()?.start_date;
    return this.data()?.panchanga_days.find((day) => day.date === date) ?? null;
  });
  protected readonly events = computed<CalendarEvent[]>(() => {
    const date = this.selectedDate() || this.data()?.start_date;
    return date ? this.data()?.by_date[date] ?? [] : [];
  });
  protected readonly dayFestivals = computed(() => {
    const date = this.selectedDate() || this.data()?.start_date;
    return date ? this.festivalRows().filter((festival) => festival.occurs_on === date) : [];
  });

  constructor() {
    effect(() => {
      void this.load(this.activeId());
    });
  }

  protected reload(): void {
    void this.load(this.activeId());
  }

  protected dateLabel(date: string): string {
    const value = date || this.data()?.start_date;
    if (!value) return 'Calendar day';
    return new Intl.DateTimeFormat('en', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date(`${value}T12:00:00`));
  }

  protected daySubhead(): string {
    const day = this.day();
    if (!day) return 'No panchanga details returned';
    return `${day.tithi} · ${day.nakshatra} · ${day.vara}`;
  }

  protected symbolForTithi(value: string): MobileSymbol {
    return tithiSymbol(value);
  }

  protected symbolForNakshatra(value: string): MobileSymbol {
    return nakshatraSymbol(value);
  }

  protected qualityLabel(day: CalendarDaySummary): string {
    return day.tarabala.favourable && day.chandrabala.favourable ? 'Good day for you' : 'Use extra care today';
  }

  protected qualityDetail(day: CalendarDaySummary): string {
    return `Tarabala ${day.tarabala.favourable ? 'favourable' : 'challenging'} · Chandrabala ${day.chandrabala.favourable ? 'strong' : 'weak'}`;
  }

  protected windows(day: CalendarDaySummary): Array<PanchangaWindow & { tone: 'good' | 'bad' }> {
    return [
      ...day.windows.auspicious.map((window) => ({ ...window, tone: 'good' as const })),
      ...day.windows.inauspicious.map((window) => ({ ...window, tone: 'bad' as const })),
    ].sort((a, b) => a.start_iso.localeCompare(b.start_iso));
  }

  protected periods(data: CalendarIntelligencePayload): string[][] {
    const current = data.current.dasha;
    return [
      ['MAHA', current.mahadasha?.lord ?? '-'],
      ['ANTAR', current.antardasha?.lord ?? '-'],
      ['PRATYANTAR', current.pratyantardasha?.lord ?? '-'],
    ];
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
      if (!this.selectedDate()) this.selectedDate.set(calendar.start_date);
      void this.loadFestivals(calendar.start_date, 60);
    } catch (error) {
      if (request === this.requestId) this.error.set((error as Error).message);
    } finally {
      if (request === this.requestId) this.loading.set(false);
    }
  }

  private async loadFestivals(fromDate: string, days: number): Promise<void> {
    const place = this.preferences.panchangaPlace();
    const profile = this.store.active();
    const city = place?.city || profile?.birth_city;
    const nation = place?.nation || profile?.birth_nation || 'IN';
    if (!city) return;
    try {
      const payload = await this.festivals.upcoming(city, nation, fromDate, days);
      this.festivalRows.set(payload.festivals);
    } catch {
      this.festivalRows.set([]);
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
