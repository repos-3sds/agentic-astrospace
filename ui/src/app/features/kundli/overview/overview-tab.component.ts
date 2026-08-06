import { Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AgGridAngular } from 'ag-grid-angular';
import { ColDef } from 'ag-grid-community';
import { LucideAngularModule } from 'lucide-angular';
import { ButtonModule } from 'primeng/button';

import { planetGlyph } from '../../../core/glyphs';
import { KundliStore } from '../../../core/kundli.store';
import {
  DailyGuidancePayload,
  MasaPayload,
  TransitAnalysisPayload,
  TransitAspect,
  TransitRule,
  TransitTimelineEvent,
} from '../../../core/models';
import { ThemeService } from '../../../core/theme.service';
import { VedicService } from '../../../core/vedic.service';
import { DefListComponent, DefRow } from '../../../shared/def-list/def-list.component';
import { GlyphBadgeComponent } from '../../../shared/glyph-badge/glyph-badge.component';
import { darkGridTheme, lightGridTheme } from '../../../shared/grid-theme';
import { SectionCardComponent } from '../../../shared/section-card/section-card.component';

interface PlanetRow {
  planet: string;
  sign: string;
  degree: number;
  house: number | string;
  retrograde: boolean;
}

interface TodaySignal {
  title: string;
  detail: string;
  label: string;
  tone: string;
  strength: number;
}

@Component({
  selector: 'app-overview-tab',
  imports: [
    RouterLink,
    AgGridAngular,
    LucideAngularModule,
    ButtonModule,
    SectionCardComponent,
    GlyphBadgeComponent,
    DefListComponent,
  ],
  templateUrl: './overview-tab.component.html',
  styleUrl: './overview-tab.component.scss',
})
export class OverviewTabComponent {
  private store = inject(KundliStore);
  private theme = inject(ThemeService);
  private vedic = inject(VedicService);

  protected readonly kundli = this.store.active;
  protected readonly transits = signal<TransitAnalysisPayload | null>(null);
  protected readonly transitError = signal<string | null>(null);
  protected readonly masa = signal<MasaPayload | null>(null);
  protected readonly daily = signal<DailyGuidancePayload | null>(null);
  protected readonly transitLoading = computed(
    () => !this.transits() && !this.transitError() && !!this.store.activeId(),
  );
  protected readonly gridTheme = computed(() =>
    this.theme.dark() ? darkGridTheme : lightGridTheme,
  );

  protected readonly bigThree = computed(() => {
    const k = this.kundli();
    return [
      { label: 'Sun sign', sign: k?.sun_sign },
      { label: 'Moon sign', sign: k?.moon_sign },
      { label: 'Ascendant', sign: k?.ascendant },
    ];
  });

  protected readonly planetRows = computed<PlanetRow[]>(() => {
    const planets = this.kundli()?.chart_data?.planets ?? {};
    return Object.entries(planets).map(([planet, p]) => ({
      planet,
      sign: p.sign ?? '—',
      degree: p.degree ?? 0,
      house: p.house ?? '—',
      retrograde: !!p.retrograde,
    }));
  });

  protected readonly birthRows = computed<DefRow[]>(() => {
    const k = this.kundli();
    if (!k) return [];
    const pad = (n: number) => String(n).padStart(2, '0');
    return [
      { label: 'Date', value: `${k.birth_year}-${pad(k.birth_month)}-${pad(k.birth_day)}` },
      { label: 'Time', value: `${pad(k.birth_hour)}:${pad(k.birth_minute)}` },
      { label: 'City', value: k.birth_city },
      { label: 'Country', value: k.birth_nation },
      { label: 'Relation', value: k.relation },
    ];
  });

  protected readonly todaySignals = computed<TodaySignal[]>(() => {
    const t = this.transits();
    if (!t) return [];
    const fromRules = t.gochara.active_rules.slice(0, 3).map((rule) => this.ruleSignal(rule));
    const fromAspect = t.strongest_aspect ? [this.aspectSignal(t.strongest_aspect)] : [];
    const fromTimeline = t.timeline.next_7_days.slice(0, 2).map((event) => this.timelineSignal(event));
    return [...fromRules, ...fromAspect, ...fromTimeline]
      .sort((a, b) => b.strength - a.strength)
      .slice(0, 4);
  });

  protected readonly strongestTransit = computed(() => this.transits()?.strongest_aspect ?? null);

  protected readonly masaRows = computed<DefRow[]>(() => {
    const m = this.masa();
    if (!m) return [];
    const rows: DefRow[] = [
      { label: 'Masa (amanta)', value: m.name },
      { label: 'Paksha', value: m.paksha },
    ];
    if (m.samvatsara) {
      rows.push({
        label: 'Samvatsara',
        value: `${m.samvatsara.name} · Shaka ${m.samvatsara.shaka_year}`,
        unverified: m.samvatsara.source_status === 'convention_dependent',
      });
    }
    if (m.ritu) rows.push({ label: 'Ritu', value: m.ritu });
    if (m.ayana) rows.push({ label: 'Ayana', value: m.ayana });
    return rows;
  });

  constructor() {
    effect(() => {
      const id = this.store.activeId();
      this.transits.set(null);
      this.transitError.set(null);
      this.masa.set(null);
      this.daily.set(null);
      if (!id) return;
      this.vedic
        .transits(id)
        .then((payload) => this.transits.set(payload))
        .catch((e) => this.transitError.set((e as Error).message));
      this.vedic
        .masa(id)
        .then((payload) => this.masa.set(payload))
        .catch(() => this.masa.set(null));
      this.vedic
        .dailyGuidance(id)
        .then((payload) => this.daily.set(payload))
        .catch(() => this.daily.set(null));
    });
  }

  protected readonly columns: ColDef<PlanetRow>[] = [
    {
      field: 'planet',
      headerName: 'Planet',
      flex: 1.3,
      cellRenderer: (p: { value: string }) =>
        `<span class="cell-glyph">${planetGlyph(p.value)}</span> ${p.value}`,
    },
    { field: 'sign', headerName: 'Sign', flex: 1.1 },
    {
      field: 'degree',
      headerName: 'Degree',
      flex: 0.8,
      valueFormatter: (p) => `${p.value}°`,
      cellClass: 'as-num',
    },
    {
      field: 'house',
      headerName: 'House',
      flex: 0.7,
      valueFormatter: (p) => (p.value === '—' ? '—' : `H${p.value}`),
      cellClass: 'as-num',
    },
    {
      field: 'retrograde',
      headerName: 'Motion',
      flex: 0.9,
      cellRenderer: (p: { value: boolean }) =>
        p.value ? '<span class="cell-retro">Retrograde</span>' : 'Direct',
    },
  ];

  protected dailyEyebrow(d: DailyGuidancePayload): string {
    const rel = this.kundli()?.relation;
    const name = this.kundli()?.name ?? 'This profile';
    const who = rel === 'self' ? 'Your day' : `${name}’s day`;
    return `${who} · ${d.vara}`;
  }

  protected dailyHeroText(d: DailyGuidancePayload): string {
    const text = d.reading?.summary?.trim() || d.verdict.text.trim();
    const firstSentence = text.match(/^.*?[.!?](?:\s|$)/)?.[0]?.trim();
    const summary = firstSentence && firstSentence.length <= 190 ? firstSentence : text;
    if (summary.length <= 190) return summary;
    return `${summary.slice(0, 184).trimEnd()}...`;
  }

  protected timingChip(d: DailyGuidancePayload): string {
    const rahu = d.muhurta_windows.find((w) => w.name.startsWith('Rahu Kalam'))?.time;
    return rahu ? `Routine ${rahu}` : 'Check windows';
  }

  protected numbersAgree(d: DailyGuidancePayload): boolean {
    return d.lucky_numbers.numerology.number === d.lucky_numbers.astrological.number;
  }

  protected luckyNumberCaption(d: DailyGuidancePayload): string {
    const n = d.lucky_numbers.numerology;
    const a = d.lucky_numbers.astrological;
    if (n.number === a.number) {
      return `Birth date and Lagna lord (${a.planet}) agree on ${n.number}.`;
    }
    return `${n.number} from birth date · ${a.number} from Lagna lord (${a.planet}).`;
  }

  protected contextDashaLabel(d: DailyGuidancePayload): string {
    return d.context.dasha_chain.map((row) => row.lord).join(' / ') || '—';
  }

  protected contextGocharaLabel(d: DailyGuidancePayload): string {
    return d.context.active_gochara.map((row) => row.name).join(', ');
  }

  protected toneClass(tone: string): string {
    if (tone === 'supportive') return 'supportive';
    if (tone === 'challenging' || tone === 'hard' || tone === 'high' || tone === 'medium' || tone === 'mixed') {
      return 'challenging';
    }
    return 'neutral';
  }

  protected aspectLabel(aspect: TransitAspect | null): string {
    if (!aspect) return 'No major aspect';
    return `${aspect.transit_planet} ${aspect.aspect.toLowerCase()} natal ${aspect.natal_planet}`;
  }

  protected formatDate(value: string): string {
    return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric' }).format(
      new Date(`${value}T12:00:00`),
    );
  }

  private ruleSignal(rule: TransitRule): TodaySignal {
    return {
      title: rule.name,
      detail: rule.trigger,
      label: rule.planet,
      tone: rule.severity,
      strength: rule.severity === 'high' ? 95 : rule.severity === 'supportive' ? 82 : 72,
    };
  }

  private aspectSignal(aspect: TransitAspect): TodaySignal {
    return {
      title: this.aspectLabel(aspect),
      detail: `${aspect.transit_sign} to ${aspect.natal_sign} · orb ${aspect.orb}°`,
      label: `${aspect.strength}%`,
      tone: aspect.tone,
      strength: aspect.strength,
    };
  }

  private timelineSignal(event: TransitTimelineEvent): TodaySignal {
    return {
      title: event.title,
      detail: `${this.formatDate(event.date)} · ${event.detail}`,
      label: event.planet,
      tone: event.tone,
      strength: event.strength,
    };
  }
}
