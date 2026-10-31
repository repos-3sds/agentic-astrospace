import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';

import { FestivalService, festivalPlace, festivalRegionsLabel } from '../../../core/festival.service';
import { KundliStore } from '../../../core/kundli.store';
import { CalendarDaySummary, CalendarEvent, CalendarIntelligencePayload, CalendarPractitionerDayDetail, FestivalOccurrence, PanchangaWindow } from '../../../core/models';
import { PreferencesService } from '../../../core/preferences.service';
import { timingClockNote, timingPlaceLabel } from '../../../core/timing-place';
import { VedicService } from '../../../core/vedic.service';
import { FestivalSheetComponent } from './festival-sheet.component';
import { calendarDayCacheOptions } from './calendar-cache-options';
import { MobileSymbol, nakshatraSymbol, tithiSymbol } from '../symbols/mobile-symbols';
import { GenericErrorComponent } from '../states/generic-error.component';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { PullRefreshService } from '../../../core/pull-refresh.service';
import { tabletLayout } from '../../../core/screen-size';
import { StickyBarDirective } from '../shared/sticky-bar.directive';

const HARD_TARAS = new Set(['Janma', 'Vadha']);

const ASPECT_WORDS: Record<string, string> = {
  conjunction: 'meets',
  opposition: 'faces',
  square: 'presses on',
  trine: 'flows with',
  sextile: 'helps',
};

/**
 * A malformed ?date= looped on "Check the date" with only Try again (U33);
 * it now opens today instead.
 */
function validDate(raw: string | null): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(raw ?? '');
  if (!match) return '';
  const [year, month, day] = [Number(match[1]), Number(match[2]), Number(match[3])];
  const date = new Date(Date.UTC(year, month - 1, day));
  const real = date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
  return real && year >= 1900 && year <= 2100 ? raw! : '';
}

/**
 * "favourable until 11:34 am, then challenging" when the star (or the Moon's
 * sign) changes before 9 pm on the day's own date; the sunrise value alone
 * otherwise. A change in the small hours before the next sunrise belongs to
 * tomorrow's morning. Times are the "HH:MM" the engine gives on the timings
 * place's clock, and from_iso is on the same clock.
 */
function changing<T extends { favourable: boolean; from?: string | null; from_iso?: string | null }>(
  periods: T[] | undefined, atSunrise: { favourable: boolean }, word: (p: { favourable: boolean }) => string,
): string {
  const day = periods?.[0]?.from_iso?.slice(0, 10);
  const waking = (periods ?? []).filter((p, i) => i === 0
    || (p.from != null && Number(p.from.slice(0, 2)) < 21 && (!day || p.from_iso?.slice(0, 10) === day)));
  const parts = waking.filter((p, i) => i === 0 || p.favourable !== waking[i - 1].favourable);
  if (parts.length < 2) return word(atSunrise);
  return parts.map((p, i) => (i === 0 ? word(p) : `then ${word(p)} from ${twelveHour(p.from!)}`)).join(', ');
}

function twelveHour(hhmm: string): string {
  const [h, m] = hhmm.split(':').map(Number);
  return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${h < 12 ? 'am' : 'pm'}`;
}

@Component({
  selector: 'as-calendar-day',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [StickyBarDirective, BackLinkDirective, GenericErrorComponent, FestivalSheetComponent],
  template: `
    @if (!embedded()) {
      <a class="mcald-back" asStickyBar [asBack]="['/m','calendar']"><img src="mobile/back.svg" alt="" /><span>Calendar</span></a>
    }
    <main class="mcald-body">
      @if (loading()) {
        <section class="mcald-state"><b>Loading day</b><p>Checking timing signals for {{ activeName() }}.</p></section>
      } @else if (error()) {
        <as-generic-error role="alert" [message]="error()!" (retried)="reload()" />
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
        <header>
          <h1>{{ dateLabel(selectedDate()) }}</h1>
          <p>{{ daySubhead() }}</p>
          <p class="mcald-place">{{ clockNote(calendar) }}</p>
        </header>

        @if (day(); as summary) {
          <section class="mcald-quality" [class.bad]="dayTone(summary) === 'care'" [class.mixed]="dayTone(summary) === 'mixed'">
            <span><img [src]="toneIcon(summary)" alt="" /></span>
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
              <div><small>PLACE</small><b>{{ placeLabel(calendar) }}</b></div>
              @for (row of masaRows(summary); track row.label) {
                <div><small>{{ row.label }}</small><b>{{ row.value }}</b><p>{{ row.note }}</p></div>
              }
            </section>

            @if (detailLoading()) {
              <section class="mcald-state" role="status">
                <b>Loading practitioner detail</b>
                <p>Calculating the selected day's Hora, Gulika, Mandi, and full timing windows.</p>
              </section>
            } @else {
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
              <small>{{ regionsLabel(festival.regions) }}</small>
              <b>{{ festival.name }}</b>
              <p>{{ festival.description || festival.prep_guidance || 'Tap for observance details.' }}</p>
              @if (festival.is_convention_dependent) {
                <p class="convention">Varies by tradition. {{ festival.observance_note || 'Date may vary by family sampradaya or regional panchangam.' }}</p>
              }
            </button>
          } @empty {
            <div><small>NONE</small><b>No festival on this day</b></div>
          }
        </section>

        <!-- Guided is Balanced without these two technical sections. -->
        @if (preferences.experienceMode() !== 'guided') {
          <p class="mcald-title">RELATED SIGNALS</p>
          <section class="mcald-stack">
            @for (event of events(); track event.title + event.date) {
              <div><small>{{ event.category }}</small><b>{{ signalTitle(event) }}</b><p>{{ signalSummary(event) }}</p></div>
            } @empty {
              <div><small>NONE</small><b>No profile-specific events returned</b></div>
            }
          </section>

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
  /** Shown inside Calendar on tablets, beside or below the month. */
  readonly embedded = input(false);
  private requestId = 0;
  private renderedRequestKey: string | null = null;

  protected readonly data = signal<CalendarIntelligencePayload | null>(null);
  protected readonly loading = signal(false);
  protected readonly detailLoading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly festivalRows = signal<FestivalOccurrence[]>([]);
  protected readonly selectedFestival = signal<FestivalOccurrence | null>(null);
  protected readonly staleNotice = signal<string | null>(null);
  protected readonly selectedDate = signal(validDate(this.route.snapshot.queryParamMap.get('date')));
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
    inject(DestroyRef).onDestroy(inject(PullRefreshService).register('/m/calendar/day', () => this.load(this.activeId(), true)));
    // On a tablet the day lives inside Calendar, so a link here (Today's
    // timing note, a push) opens Calendar on that date instead.
    const router = inject(Router);
    const tablet = tabletLayout();
    effect(() => {
      if (this.embedded() || !tablet()) return;
      const date = untracked(() => this.selectedDate());
      void router.navigate(['/m', 'calendar'], { queryParams: date ? { date } : {}, replaceUrl: true });
    });
    this.route.queryParamMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => {
        this.selectedDate.set(validDate(params.get('date')));
      });

    effect(() => {
      const profileId = this.activeId();
      this.selectedDate();
      this.preferences.panchangaContextKey();
      this.preferences.experienceMode();
      void this.load(profileId);
    });
    effect(() => {
      const regions = this.preferences.festivalRegions();
      const startDate = this.data()?.start_date;
      if (startDate) void this.loadFestivals(startDate, regions);
    });
  }

  protected reload(): void {
    void this.load(this.activeId(), true);
  }

  protected readonly regionsLabel = festivalRegionsLabel;

  protected dateLabel(date: string): string {
    const value = date || this.data()?.start_date;
    if (!value) return 'Calendar day';
    return new Intl.DateTimeFormat('en', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date(`${value}T12:00:00`));
  }

  /** Whose clock the windows are in; the audit found them read as the phone's. */
  protected clockNote(calendar: CalendarIntelligencePayload): string {
    return timingClockNote(calendar.place);
  }

  protected placeLabel(calendar: CalendarIntelligencePayload): string {
    return timingPlaceLabel(calendar.place);
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

  /**
   * The same rule that tints the month grid (panchanga_day.day_quality), so a
   * tapped day never disagrees with its cell (U14): take care on Chandrashtama
   * or a Janma or Vadha tara, good when both balas are good, mixed otherwise.
   */
  protected dayTone(day: CalendarDaySummary): 'good' | 'mixed' | 'care' {
    if (day.chandrabala.chandrashtama || day.chandrabala.house_from_rashi === 8
      || HARD_TARAS.has(day.tarabala.tara)) return 'care';
    return day.tarabala.favourable && day.chandrabala.favourable ? 'good' : 'mixed';
  }

  protected toneIcon(day: CalendarDaySummary): string {
    const tone = this.dayTone(day);
    return tone === 'good' ? 'mobile/cancellation-check.svg' : tone === 'care' ? 'mobile/alert-triangle.svg' : 'mobile/info.svg';
  }

  protected qualityLabel(day: CalendarDaySummary): string {
    const tone = this.dayTone(day);
    if (tone === 'good') return 'Good day for you';
    if (tone === 'mixed') return 'A mixed day';
    // Named for the flag that set it, and true of any date, not only today.
    // Today's ring stays under 50 on these days too (daily.py _is_care_day).
    const isChandrashtama = day.chandrabala.chandrashtama || day.chandrabala.house_from_rashi === 8;
    return isChandrashtama ? 'Take care: Chandrashtama day' : `Take care: ${day.tarabala.tara} star day`;
  }

  protected qualityDetail(day: CalendarDaySummary): string {
    const tara = (favourable: boolean) => (favourable ? 'favourable' : 'challenging');
    const moon = (favourable: boolean) => (favourable ? 'strong' : 'weak');
    return `Tarabala ${changing(day.tarabala_periods, day.tarabala, (p) => tara(p.favourable))}`
      + ` · Chandrabala ${changing(day.chandrabala_periods, day.chandrabala, (p) => moon(p.favourable))}`;
  }

  protected windows(day: CalendarDaySummary): Array<PanchangaWindow & { tone: 'good' | 'bad' }> {
    const windows = day.practitioner_detail?.windows ?? day.windows;
    return [
      ...(windows.auspicious ?? []).map((window) => ({ ...window, tone: 'good' as const })),
      ...(windows.inauspicious ?? []).map((window) => ({ ...window, tone: 'bad' as const })),
    ].sort((a, b) => a.start_iso.localeCompare(b.start_iso));
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

  /**
   * Month and day-definition rows, each stating the convention used. The
   * engine computes amanta and derives the purnimanta name beside it; a
   * practitioner from a purnimanta region needs the second name, not a hint.
   */
  protected masaRows(day: CalendarDaySummary): { label: string; value: string; note: string }[] {
    const detail = day.practitioner_detail;
    const masa = detail?.masa;
    const rows: { label: string; value: string; note: string }[] = [];
    if (masa?.amanta) {
      const adhika = masa.adhika ? 'Adhika ' : '';
      rows.push({
        label: 'Masa (amanta)',
        value: `${adhika}${masa.amanta}${masa.paksha ? ` · ${masa.paksha} paksha` : ''}`,
        note: 'Month ends at the new moon — the reckoning used throughout this app.',
      });
      if (masa.purnimanta && masa.purnimanta !== masa.amanta) {
        rows.push({
          label: 'Masa (purnimanta)',
          value: `${adhika}${masa.purnimanta}`,
          note: 'Month ends at the full moon — North Indian reckoning; convention-dependent.',
        });
      }
    }
    if (detail?.conventions?.day_definition) {
      rows.push({
        label: 'Day definition',
        value: detail.conventions.day_definition,
        note: detail.conventions.verify_pending?.length
          ? `Tables still being verified: ${detail.conventions.verify_pending.join(', ')}.`
          : 'All timing tables verified against the sources in the KB manifest.',
      });
    }
    return rows;
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
      this.renderedRequestKey = null;
      this.loading.set(false);
      this.detailLoading.set(false);
      return;
    }

    const options = this.calendarOptions();
    const selectedDate = this.selectedDate() || this.localDate();
    const requestKey = [
      id,
      selectedDate,
      this.preferences.panchangaContextKey(),
      options.includePractitionerDetail ? 'practitioner' : 'standard',
    ].join('|');
    const dayOptions = { ...options, asOf: selectedDate };
    const cached = this.vedic.cachedCalendarIntelligenceEntry(id, 1, undefined, dayOptions);
    if (cached && !forceRefresh) {
      this.data.set(cached.data);
      if (!this.selectedDate()) this.selectedDate.set(cached.data.start_date);
      this.renderedRequestKey = requestKey;
      this.loading.set(false);
      this.detailLoading.set(false);
      void this.loadFestivals(cached.data.start_date);
      if (cached.freshness === 'stale') {
        this.staleNotice.set(`Showing saved results for ${cached.data.place.city} while details refresh.`);
        void this.refreshCalendar(id, request);
      }
      return;
    }

    // A month summary is enough to render the selected day immediately.
    // Practitioner-only rows then replace it with a bounded one-day payload.
    const monthCached = this.vedic.cachedCalendarIntelligenceEntry(
      id,
      45,
      undefined,
      { includePractitionerDetail: false },
    );
    const monthContainsDate = monthCached?.data.panchanga_days.some((day) => day.date === selectedDate);
    if (!forceRefresh && monthCached && monthContainsDate) {
      this.data.set(monthCached.data);
      this.renderedRequestKey = requestKey;
      this.loading.set(false);
      void this.loadFestivals(monthCached.data.start_date);
      if (!options.includePractitionerDetail) return;
    } else if (this.renderedRequestKey !== requestKey) {
      this.data.set(null);
    }

    if (!this.data()) this.loading.set(true);
    this.detailLoading.set(options.includePractitionerDetail && !!this.data());
    try {
      const calendar = forceRefresh
        ? await this.vedic.refreshCalendarIntelligence(id, 1, undefined, dayOptions)
        : await this.vedic.calendarIntelligence(id, 1, undefined, dayOptions);
      if (request !== this.requestId || this.activeId() !== id) return;
      this.data.set(calendar);
      if (!this.selectedDate()) this.selectedDate.set(calendar.start_date);
      this.renderedRequestKey = requestKey;
      void this.loadFestivals(calendar.start_date);
    } catch (error) {
      if (request === this.requestId) {
        const fallback = this.vedic.cachedCalendarIntelligenceEntry(id, 1, undefined, dayOptions) ?? monthCached;
        if (fallback && fallback.data.panchanga_days.some((day) => day.date === selectedDate)) {
          this.data.set(fallback.data);
          if (!this.selectedDate()) this.selectedDate.set(fallback.data.start_date);
          this.renderedRequestKey = requestKey;
          this.staleNotice.set(`Showing last loaded results for ${fallback.data.place.city}. ${this.friendlyError(error)}`);
          void this.loadFestivals(fallback.data.start_date);
        } else {
          this.error.set((error as Error).message);
        }
      }
    } finally {
      if (request === this.requestId) {
        this.loading.set(false);
        this.detailLoading.set(false);
      }
    }
  }

  private async refreshCalendar(id: string, request: number): Promise<void> {
    const selectedDate = this.selectedDate() || this.localDate();
    try {
      const calendar = await this.vedic.refreshCalendarIntelligence(
        id,
        1,
        undefined,
        { ...this.calendarOptions(), asOf: selectedDate },
      );
      if (request !== this.requestId || this.activeId() !== id) return;
      this.data.set(calendar);
      if (!this.selectedDate()) this.selectedDate.set(calendar.start_date);
      void this.loadFestivals(calendar.start_date);
    } catch (error) {
      if (request === this.requestId && this.data()) {
        this.staleNotice.set(`Showing saved results. ${this.friendlyError(error)}`);
      }
    }
  }

  private calendarOptions(): { includePractitionerDetail: boolean } {
    return calendarDayCacheOptions(this.preferences.experienceMode());
  }

  private localDate(): string {
    try {
      return new Intl.DateTimeFormat('en-CA', {
        timeZone: this.preferences.effectiveTimezone(),
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      }).format(new Date());
    } catch {
      return new Date().toISOString().slice(0, 10);
    }
  }

  /**
   * Festivals for the month the day sits in. That is the window the Calendar
   * month view already asked for, so a tapped day reads it from cache instead
   * of asking the server for a fresh window starting on every date.
   */
  private async loadFestivals(fallbackDate: string, regions = this.preferences.festivalRegions()): Promise<void> {
    const date = this.selectedDate() || fallbackDate;
    const place = festivalPlace(this.preferences, this.store.owner() ?? this.store.active());
    if (!place || !/^\d{4}-\d{2}/.test(date)) return;
    const fromDate = `${date.slice(0, 7)}-01`;
    const days = new Date(Number(date.slice(0, 4)), Number(date.slice(5, 7)), 0).getDate();
    const cached = this.festivals.cachedUpcoming(place, fromDate, days, regions);
    if (cached) {
      this.festivalRows.set(cached.festivals);
      return;
    }
    try {
      const payload = await this.festivals.upcoming(place, fromDate, days, regions);
      this.festivalRows.set(payload.festivals);
    } catch {
      this.festivalRows.set([]);
    }
  }

  /** Western aspect words read as plain English outside Practitioner (U14). */
  protected signalTitle(event: CalendarEvent): string {
    if (this.preferences.experienceMode() === 'practitioner') return event.title;
    return event.title.replace(
      /^(\w+) (conjunction|opposition|square|trine|sextile) natal (\w+)$/i,
      (_m, moving: string, aspect: string, natal: string) => `${moving} ${ASPECT_WORDS[aspect.toLowerCase()]} your ${natal}`,
    );
  }

  protected signalSummary(event: CalendarEvent): string {
    if (this.preferences.experienceMode() === 'practitioner') return event.detail;
    const hard = event.tone === 'challenging' || event.tone === 'hard';
    if (event.category === 'dasha') return 'The life period shaping this stretch for you.';
    if (event.category === 'transit') {
      return hard
        ? 'A slower stretch. Go gently with big moves while it lasts.'
        : event.tone === 'supportive'
          ? 'A helpful movement for you. A good time to put in effort.'
          : 'A background movement in your chart. Nothing to act on.';
    }
    return hard ? 'Go gently around this time.' : event.tone === 'supportive' ? 'Helpful timing for you.' : 'Background timing from your chart.';
  }

  private friendlyError(error: unknown): string {
    const message = (error as Error).message || 'Network request failed.';
    return message.includes('Failed to fetch') ? 'Network request failed.' : message;
  }
}
