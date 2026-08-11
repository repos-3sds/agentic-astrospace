import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { FestivalService } from '../../../core/festival.service';
import { KundliStore } from '../../../core/kundli.store';
import { CalendarDaySummary, CalendarEvent, CalendarIntelligencePayload, CalendarPractitionerDayDetail, FestivalOccurrence, PanchangaWindow } from '../../../core/models';
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
        @if (staleNotice()) {
          <section class="mcald-stale" role="status">
            <b>You're offline</b>
            <p>{{ staleNotice() }}</p>
            <button type="button" (click)="reload()">Retry</button>
          </section>
        }
        <header><h1>{{ dateLabel(selectedDate()) }}</h1><p>{{ daySubhead() }}</p></header>

        @if (day(); as summary) {
          <section class="mcald-quality" [class.bad]="!summary.tarabala.favourable || !summary.chandrabala.favourable">
            <span><img src="mobile/cancellation-check.svg" alt="" /></span>
            <div><b>{{ qualityLabel(summary) }}</b><small>{{ qualityDetail(summary) }}</small></div>
          </section>

          @if (preferences.experienceMode() === 'guided') {
            <p class="mcald-title accent">WHAT TO NOTICE</p>
            <section class="mcald-guided">
              <article>
                <img src="mobile/trending-up.svg" alt="" aria-hidden="true" />
                <span><small>GOOD WINDOW</small><b>{{ guidedGoodWindow(summary) }}</b></span>
              </article>
              <article>
                <img src="mobile/alert-triangle.svg" alt="" aria-hidden="true" />
                <span><small>USE CARE</small><b>{{ guidedAvoidWindow(summary) }}</b></span>
              </article>
              <a [routerLink]="['/m', 'ask']" [queryParams]="{ q: 'What should I do on ' + dateLabel(selectedDate()) + '?' }">
                Ask about this date
                <img src="mobile/chevron.svg" alt="" aria-hidden="true" />
              </a>
            </section>
          } @else {
            <p class="mcald-title accent">DAY TIMELINE</p>
            <section class="mcald-list">
              @for (row of windows(summary); track row.name + row.start_iso) {
                <div [class.bad]="row.tone === 'bad'"><i></i><span><b>{{ row.name }}</b><small>{{ row.start }} - {{ row.end }}</small></span><em>{{ row.tone === 'bad' ? 'AVOID' : 'GOOD' }}</em></div>
              } @empty {
                <p>No timing windows were returned for this day.</p>
              }
            </section>
          }

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

            <p class="mcald-title">PRACTITIONER WINDOWS</p>
            <section class="mcald-stack">
              @for (row of practitionerWindowRows(summary); track row.label) {
                <div><small>{{ row.label }}</small><b>{{ row.value }}</b><p>{{ row.note }}</p></div>
              }
            </section>

            <p class="mcald-title">GULIKA &amp; MANDI</p>
            <section class="mcald-stack">
              @for (row of upagrahaRows(summary); track row.label) {
                <div><small>{{ row.label }}</small><b>{{ row.value }}</b><p>{{ row.note }}</p></div>
              }
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

        @if (preferences.experienceMode() !== 'guided') {
          <p class="mcald-title">ACTIVE PERIOD STACK</p>
          <section class="mcald-stack">
            @for (row of periods(calendar); track row[0]) { <div><small>{{ row[0] }}</small><b>{{ row[1] }}</b></div> }
          </section>
        }
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
  private readonly destroyRef = inject(DestroyRef);
  private requestId = 0;

  protected readonly data = signal<CalendarIntelligencePayload | null>(null);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly festivalRows = signal<FestivalOccurrence[]>([]);
  protected readonly selectedFestival = signal<FestivalOccurrence | null>(null);
  protected readonly staleNotice = signal<string | null>(null);
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
    this.route.queryParamMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => {
        this.selectedDate.set(params.get('date') ?? '');
      });

    effect(() => {
      const profileId = this.activeId();
      this.preferences.panchangaContextKey();
      void this.load(profileId);
    });
    effect(() => {
      const regions = this.preferences.festivalRegions();
      const startDate = this.data()?.start_date;
      if (startDate) void this.loadFestivals(startDate, 60, regions);
    });
  }

  protected reload(): void {
    void this.load(this.activeId(), true);
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
    const windows = day.practitioner_detail?.windows ?? day.windows;
    return [
      ...(windows.auspicious ?? []).map((window) => ({ ...window, tone: 'good' as const })),
      ...(windows.inauspicious ?? []).map((window) => ({ ...window, tone: 'bad' as const })),
    ].sort((a, b) => a.start_iso.localeCompare(b.start_iso));
  }

  protected guidedGoodWindow(day: CalendarDaySummary): string {
    const good = day.windows.auspicious[0];
    return good ? `${good.name}, ${good.start} - ${good.end}` : 'No special good window returned for this day.';
  }

  protected guidedAvoidWindow(day: CalendarDaySummary): string {
    const caution = day.windows.inauspicious[0];
    return caution ? `${caution.name}, ${caution.start} - ${caution.end}` : 'No major caution window returned for this day.';
  }

  protected practitionerWindowRows(day: CalendarDaySummary): { label: string; value: string; note: string }[] {
    const detail = day.practitioner_detail;
    const rows = this.windows(day);
    const find = (label: string) => rows.find((row) => row.name.toLowerCase().includes(label.toLowerCase()));
    const rowFor = (label: string, match: (PanchangaWindow & { tone: 'good' | 'bad' }) | undefined, fallbackNote: string) => ({
      label,
      value: match ? `${match.start} - ${match.end}` : 'Not active in the returned day window',
      note: match?.note ?? (match ? match.name : fallbackNote),
    });
    const activeHora = this.activeHora(detail?.horas);
    return [
      activeHora,
      rowFor('Abhijit', find('Abhijit'), 'Abhijit Muhurta is not observed or not available for this date.'),
      rowFor('Amrit Kalam', find('Amrit Kalam'), 'No Amrit Kalam segment overlaps this panchanga day.'),
      rowFor('Rahu Kalam', find('Rahu Kalam'), 'Rahu Kalam was not included in the returned window set.'),
      rowFor('Yamaganda', find('Yamaganda'), 'Yamaganda was not included in the returned window set.'),
      rowFor('Gulika Kalam', find('Gulika Kalam'), 'Gulika Kalam was not included in the returned window set.'),
      rowFor('Durmuhurta', find('Durmuhurta'), 'Durmuhurta was not included in the returned window set.'),
      rowFor('Varjya', find('Varjya'), 'No Varjya segment overlaps this panchanga day.'),
      rowFor('Bhadra', find('Bhadra'), 'Bhadra is not active for this day.'),
      {
        label: 'Disha Shool',
        value: this.stringValue(detail?.disha_shool, 'No direction flagged'),
        note: 'Traditional direction to avoid for unnecessary travel starts.',
      },
      {
        label: 'Panchaka',
        value: detail?.panchaka?.active ? `Active · ${detail.panchaka.nakshatra ?? day.nakshatra}` : 'Not active',
        note: detail?.panchaka?.note ?? 'Panchaka is computed from the day nakshatra.',
      },
    ];
  }

  protected upagrahaRows(day: CalendarDaySummary): { label: string; value: string; note: string }[] {
    return [
      ...this.upagrahaPointRows('Gulika', day.gulika, 'start of Saturn portion'),
      ...this.upagrahaPointRows('Mandi', day.mandi, 'middle of Saturn portion'),
    ];
  }

  protected periods(data: CalendarIntelligencePayload): string[][] {
    const current = data.current.dasha;
    return [
      ['MAHA', current.mahadasha?.lord ?? '-'],
      ['ANTAR', current.antardasha?.lord ?? '-'],
      ['PRATYANTAR', current.pratyantardasha?.lord ?? '-'],
    ];
  }

  private upagrahaPointRows(label: string, payload: unknown, convention: string): { label: string; value: string; note: string }[] {
    if (!payload || typeof payload !== 'object') {
      return [{ label, value: 'Not returned', note: 'The day payload did not include this upagraha calculation.' }];
    }
    const data = payload as Record<string, unknown>;
    const note = typeof data['note'] === 'string' ? data['note'] : `${label} is shown using the ${convention} convention.`;
    return ['day', 'night'].map((half) => {
      const point = data[half] as Record<string, unknown> | undefined;
      return {
        label: `${label} · ${half}`,
        value: this.upagrahaValue(point),
        note,
      };
    });
  }

  private upagrahaValue(point: Record<string, unknown> | undefined): string {
    if (!point) return 'Not returned';
    const time = typeof point['start_time'] === 'string' ? point['start_time'] : '';
    const sign = typeof point['sign'] === 'string' ? point['sign'] : '';
    const dms = typeof point['dms'] === 'string' ? point['dms'] : '';
    const longitude = typeof point['longitude'] === 'number' ? `${point['longitude'].toFixed(2)} deg` : '';
    return [time, [sign, dms || longitude].filter(Boolean).join(' ')].filter(Boolean).join(' · ') || 'Returned by backend';
  }

  private activeHora(horas: CalendarPractitionerDayDetail['horas'] | null | undefined): { label: string; value: string; note: string } {
    const rows = Array.isArray(horas)
      ? horas
      : [
          ...((horas?.day) ?? []),
          ...((horas?.night) ?? []),
        ];
    const now = Date.now();
    const active = rows.find((row) => {
      const start = new Date(row.start_iso).getTime();
      const end = new Date(row.end_iso).getTime();
      return Number.isFinite(start) && Number.isFinite(end) && start <= now && now < end;
    }) ?? rows[0];
    return {
      label: 'Hora',
      value: active ? `${active.name.replace(' Hora', '')} · ${active.start} - ${active.end}` : 'No hora rows returned',
      note: active?.note ?? 'Planetary hour from sunrise/sunset divisions.',
    };
  }

  private stringValue(value: unknown, fallback: string): string {
    return typeof value === 'string' && value.trim() ? value : fallback;
  }

  private async load(id: string | null, forceRefresh = false): Promise<void> {
    const request = ++this.requestId;
    this.error.set(null);
    this.staleNotice.set(null);
    if (!id) {
      this.data.set(null);
      this.loading.set(false);
      return;
    }

    const cached = this.vedic.cachedCalendarIntelligence(id, 45, undefined, { includePractitionerDetail: true });
    if (cached && !forceRefresh) {
      this.data.set(cached);
      if (!this.selectedDate()) this.selectedDate.set(cached.start_date);
      this.loading.set(false);
      void this.loadFestivals(cached.start_date, 60);
      void this.refreshCalendar(id, request);
      return;
    }

    if (!this.data()) this.loading.set(true);
    try {
      const calendar = forceRefresh
        ? await this.vedic.refreshCalendarIntelligence(id, 45, undefined, { includePractitionerDetail: true })
        : await this.vedic.calendarIntelligence(id, 45, undefined, { includePractitionerDetail: true });
      if (request !== this.requestId || this.activeId() !== id) return;
      this.data.set(calendar);
      if (!this.selectedDate()) this.selectedDate.set(calendar.start_date);
      void this.loadFestivals(calendar.start_date, 60);
    } catch (error) {
      if (request === this.requestId) {
        const cached = this.vedic.cachedCalendarIntelligence(id, 45, undefined, { includePractitionerDetail: true });
        if (cached) {
          this.data.set(cached);
          if (!this.selectedDate()) this.selectedDate.set(cached.start_date);
          this.staleNotice.set(`Showing last loaded results for ${cached.place.city}. ${this.friendlyError(error)}`);
          void this.loadFestivals(cached.start_date, 60);
        } else {
          this.error.set((error as Error).message);
        }
      }
    } finally {
      if (request === this.requestId) this.loading.set(false);
    }
  }

  private async refreshCalendar(id: string, request: number): Promise<void> {
    try {
      const calendar = await this.vedic.refreshCalendarIntelligence(id, 45, undefined, { includePractitionerDetail: true });
      if (request !== this.requestId || this.activeId() !== id) return;
      this.data.set(calendar);
      if (!this.selectedDate()) this.selectedDate.set(calendar.start_date);
      void this.loadFestivals(calendar.start_date, 60);
    } catch (error) {
      if (request === this.requestId && this.data()) {
        this.staleNotice.set(`Showing saved results. ${this.friendlyError(error)}`);
      }
    }
  }

  private async loadFestivals(fromDate: string, days: number, regions = this.preferences.festivalRegions()): Promise<void> {
    const place = this.preferences.panchangaPlace();
    const profile = this.store.active();
    const city = place?.city || profile?.birth_city;
    const nation = place?.nation || profile?.birth_nation || 'IN';
    if (!city) return;
    const cached = this.festivals.cachedUpcoming(city, nation, fromDate, days, regions);
    if (cached) {
      this.festivalRows.set(cached.festivals);
      return;
    }
    try {
      const payload = await this.festivals.upcoming(city, nation, fromDate, days, regions);
      this.festivalRows.set(payload.festivals);
    } catch {
      this.festivalRows.set([]);
    }
  }

  private async refreshFestivals(city: string, nation: string, fromDate: string, days: number, regions = this.preferences.festivalRegions()): Promise<void> {
    try {
      const payload = await this.festivals.refreshUpcoming(city, nation, fromDate, days, regions);
      this.festivalRows.set(payload.festivals);
    } catch {
      // Keep the cached festival rows visible until a later refresh succeeds.
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

  private friendlyError(error: unknown): string {
    const message = (error as Error).message || 'Network request failed.';
    return message.includes('Failed to fetch') ? 'Network request failed.' : message;
  }
}
