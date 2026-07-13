import { Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';
import { Select } from 'primeng/select';
import { Skeleton } from 'primeng/skeleton';

import { KundliStore } from '../../../core/kundli.store';
import {
  CalendarEvent,
  CalendarIntelligencePayload,
  CalendarReadingMarker,
  PanchangaCity,
  PanchangaDay,
  PanchangaWindow,
} from '../../../core/models';
import { PanchangaService } from '../../../core/panchanga.service';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { SectionCardComponent } from '../../../shared/section-card/section-card.component';

interface TimelineBlock {
  name: string;
  time: string;
  left: number;
  width: number;
  compact: boolean;
}

interface TimelineTick {
  left: number;
  label: string;
  major: boolean;
}

interface TimelineMarker {
  left: number;
  label: string;
  kind: 'sunrise' | 'sunset' | 'next';
}

interface Pill {
  ok: boolean;
  text: string;
}

@Component({
  selector: 'app-calendar-tab',
  imports: [FormsModule, LucideAngularModule, RouterLink, Select, Skeleton, SectionCardComponent],
  templateUrl: './calendar-tab.component.html',
  styleUrl: './calendar-tab.component.scss',
})
export class CalendarTabComponent {
  private store = inject(KundliStore);
  private vedic = inject(VedicService);
  private panchangaSvc = inject(PanchangaService);
  private prefs = inject(PreferencesService);

  protected readonly data = signal<CalendarIntelligencePayload | null>(null);
  protected readonly todayData = signal<PanchangaDay | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly cityOptions = signal<PanchangaCity[]>([]);
  protected readonly selectedPlace = signal<PanchangaCity | null>(null);
  protected readonly mode = signal<'today' | 'seven' | 'thirty'>('today');
  protected readonly section = signal<'panchanga' | 'signals' | 'timeline' | 'feed'>('panchanga');
  protected readonly browserTimezone = this.panchangaSvc.browserTimezone();
  protected readonly loading = computed(() => (!this.data() || !this.todayData()) && !this.error());

  protected readonly todayEvents = computed(() => {
    const d = this.data();
    return d ? d.by_date[d.start_date] ?? [] : [];
  });

  protected readonly todayReadings = computed(() => this.data()?.current.readings ?? []);

  protected readonly pendingValidationCount = computed(() => {
    const readings = Object.values(this.data()?.readings_by_date ?? {}).flat();
    const claims = Object.values(this.data()?.prediction_claims_by_date ?? {}).flat();
    return (
      readings.filter((reading) => !reading.user_rating).length +
      claims.filter((claim) => claim.status === 'pending').length
    );
  });

  protected readonly visibleEvents = computed(() => {
    const d = this.data();
    if (!d) return [];
    if (this.mode() === 'today') return this.todayEvents();
    const max = this.mode() === 'seven' ? 7 : 30;
    const start = new Date(`${d.start_date}T12:00:00`);
    return d.events.filter((event) => {
      const delta = (+new Date(`${event.date}T12:00:00`) - +start) / 86400000;
      return delta >= 0 && delta <= max;
    });
  });

  protected readonly groupedEvents = computed(() => {
    const groups = new Map<string, CalendarEvent[]>();
    for (const event of this.visibleEvents()) {
      groups.set(event.date, [...(groups.get(event.date) ?? []), event]);
    }
    return [...groups.entries()].map(([date, events]) => ({
      date,
      events: events.sort((a, b) => b.strength - a.strength),
    }));
  });

  protected readonly categoryCounts = computed(() => {
    const counts = new Map<string, number>();
    for (const event of this.visibleEvents()) {
      counts.set(event.category, (counts.get(event.category) ?? 0) + 1);
    }
    return ['panchanga', 'transit', 'dasha', 'reading', 'prediction'].map((category) => ({
      category,
      count: counts.get(category) ?? 0,
    }));
  });

  constructor() {
    this.panchangaSvc
      .cities()
      .then((cities) => {
        this.cityOptions.set(cities);
        const saved = this.prefs.panchangaPlace();
        const match = saved
          ? cities.find((city) => city.city === saved.city && city.nation === saved.nation) ?? null
          : null;
        this.selectedPlace.set(match);
      })
      .catch(() => this.cityOptions.set([]));

    effect(() => {
      const id = this.store.activeId();
      const place = this.selectedPlace();
      this.data.set(null);
      this.todayData.set(null);
      this.error.set(null);
      if (!id) return;
      Promise.all([
        this.vedic.calendarIntelligence(id, 30, place),
        this.panchangaSvc.today(id, place),
      ])
        .then(([calendar, panchanga]) => {
          this.data.set(calendar);
          this.todayData.set(panchanga);
        })
        .catch((e) => this.error.set((e as Error).message));
    });
  }

  protected onPlaceChange(place: PanchangaCity | null): void {
    this.prefs.setPanchangaPlace(place);
    this.selectedPlace.set(place);
  }

  protected readonly chips = computed(() => {
    const p = this.todayData();
    if (!p) return [];
    const el = p.elements;
    const entry = (label: string, entries: { name: string; upto: string }[]) => ({
      label,
      name: entries[0]?.name ?? '—',
      upto: entries[0]?.upto,
      next: entries[1]?.name,
    });
    return [
      entry('Tithi', el.tithi),
      entry('Nakshatra', el.nakshatra),
      entry('Yoga', el.yoga),
      entry('Karana', el.karana),
      { label: 'Moon rashi', name: p.moon_rashi_at_sunrise, upto: undefined, next: undefined },
    ];
  });

  private axis = computed(() => {
    const p = this.todayData();
    if (!p) return null;
    const sunrise = new Date(`${p.date}T${p.sunrise}`);
    const firstWindow = p.windows.auspicious[0]?.start_iso;
    const start = new Date(
      Math.min(firstWindow ? +new Date(firstWindow) : +sunrise, +sunrise) - 30 * 60000,
    );
    const end = new Date(+sunrise + 25 * 3600000);
    return { start: +start, end: +end, span: +end - +start };
  });

  private leftPct(ms: number): number {
    const axis = this.axis();
    if (!axis) return 0;
    return Math.max(0, Math.min(100, ((ms - axis.start) / axis.span) * 100));
  }

  private timeLabel(ms: number): string {
    return new Intl.DateTimeFormat('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).format(new Date(ms));
  }

  protected readonly timelineTicks = computed<TimelineTick[]>(() => {
    const axis = this.axis();
    if (!axis) return [];
    const firstHour = Math.ceil(axis.start / 3600000) * 3600000;
    const ticks: TimelineTick[] = [{ left: 0, label: this.timeLabel(axis.start), major: true }];
    for (let ms = firstHour; ms < axis.end; ms += 3600000) {
      const hour = new Date(ms).getHours();
      ticks.push({ left: this.leftPct(ms), label: this.timeLabel(ms), major: hour % 3 === 0 });
    }
    ticks.push({ left: 100, label: this.timeLabel(axis.end), major: true });
    return ticks;
  });

  protected readonly timelineMarkers = computed<TimelineMarker[]>(() => {
    const p = this.todayData();
    if (!p) return [];
    const date = p.date;
    const nextDate = new Date(`${date}T${p.sunrise}`);
    nextDate.setDate(nextDate.getDate() + 1);
    const pad = (n: number) => String(n).padStart(2, '0');
    const nextDatePart = [
      nextDate.getFullYear(),
      pad(nextDate.getMonth() + 1),
      pad(nextDate.getDate()),
    ].join('-');
    return [
      { left: this.leftPct(+new Date(`${date}T${p.sunrise}`)), label: `Sunrise ${p.sunrise}`, kind: 'sunrise' },
      { left: this.leftPct(+new Date(`${date}T${p.sunset}`)), label: `Sunset ${p.sunset}`, kind: 'sunset' },
      {
        left: this.leftPct(+new Date(`${nextDatePart}T${p.next_sunrise}`)),
        label: `Next sunrise ${p.next_sunrise}`,
        kind: 'next',
      },
    ];
  });

  private toBlocks(windows: PanchangaWindow[]): TimelineBlock[] {
    const axis = this.axis();
    if (!axis) return [];
    const pct = (iso: string) =>
      Math.max(0, Math.min(100, ((+new Date(iso) - axis.start) / axis.span) * 100));
    return windows.map((w) => {
      const left = pct(w.start_iso);
      const width = Math.max(pct(w.end_iso) - left, 0.8);
      return { name: w.name, time: `${w.start}–${w.end}`, left, width, compact: width < 5 };
    });
  }

  protected readonly goodBlocks = computed(() =>
    this.toBlocks(this.todayData()?.windows.auspicious ?? []),
  );
  protected readonly badBlocks = computed(() =>
    this.toBlocks(this.todayData()?.windows.inauspicious ?? []),
  );

  protected readonly pills = computed<Pill[]>(() => {
    const per = this.todayData()?.personal;
    if (!per?.tarabala) return [];
    const out: Pill[] = [
      { ok: per.tarabala.favourable, text: `Tarabala ${per.tarabala.tara} (${per.tarabala.count}/9)` },
      {
        ok: per.chandrabala.favourable,
        text: per.chandrabala.chandrashtama
          ? 'Chandrashtama — Moon 8th from your rashi'
          : `Chandrabala — Moon ${per.chandrabala.house_from_rashi}th from rashi`,
      },
    ];
    const ghatak = (per.ghatak_alerts ?? []).filter((a) => a.matched);
    if (ghatak.length) {
      for (const a of ghatak) out.push({ ok: false, text: `Ghatak ${a.type} today (${a.ghatak_value})` });
    } else {
      out.push({ ok: true, text: 'No ghatak match today' });
    }
    return out;
  });

  protected toneClass(tone: string): string {
    if (tone === 'supportive') return 'supportive';
    if (tone === 'challenging' || tone === 'hard') return 'challenging';
    return 'neutral';
  }

  protected formatDate(value: string): string {
    return new Intl.DateTimeFormat('en', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    }).format(new Date(`${value}T12:00:00`));
  }

  protected dashaPath(data: CalendarIntelligencePayload): string {
    const current = data.current.dasha;
    return [
      current.mahadasha?.lord,
      current.antardasha?.lord,
      current.pratyantardasha?.lord,
    ].filter(Boolean).join(' / ') || '—';
  }

  protected readingTitle(reading: CalendarReadingMarker): string {
    return `${reading.reading_type} v${reading.version}`;
  }

  protected readingMeta(reading: CalendarReadingMarker): string {
    const bits = [reading.period_label || 'Generated prediction'];
    if (reading.deviation_score != null) {
      bits.push(`${reading.deviation_score}% deviation`);
    }
    bits.push(reading.feedback_status);
    return bits.join(' · ');
  }
}
