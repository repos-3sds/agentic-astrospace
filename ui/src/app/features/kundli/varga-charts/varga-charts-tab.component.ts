import { Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Select } from 'primeng/select';
import { SelectButton } from 'primeng/selectbutton';
import { Skeleton } from 'primeng/skeleton';
import { Tag } from 'primeng/tag';

import { planetGlyph } from '../../../core/glyphs';
import { KundliStore } from '../../../core/kundli.store';
import { VargaChart, VedicAll } from '../../../core/models';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import {
  KundliChartComponent,
  KundliChartStyle,
} from '../../../shared/kundli-chart/kundli-chart.component';
import { SectionCardComponent } from '../../../shared/section-card/section-card.component';

interface VargaRow {
  planet: string;
  glyph: string;
  degree: string;
  rashi: string;
  nakshatra: string;
  paada: number | string;
  rashiLord: string;
  nakshatraLord: string;
  subLord: string;
  subSubLord: string;
  vargottama: boolean;
  retrograde: boolean;
}

type ChartView = 'both' | 'chart' | 'placements';

const VARGA_LIST = [
  'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10',
  'D11', 'D12', 'D16', 'D20', 'D24', 'D27', 'D30', 'D40', 'D45', 'D60',
];

const VARGA_OPTIONS = VARGA_LIST.map((value) => ({ label: value, value }));

const VIEW_OPTIONS: { label: string; value: ChartView }[] = [
  { label: 'Both', value: 'both' },
  { label: 'Chart', value: 'chart' },
  { label: 'Placements', value: 'placements' },
];

const STYLE_OPTIONS: { label: string; value: KundliChartStyle }[] = [
  { label: 'South Indian', value: 'south' },
  { label: 'North Indian', value: 'north' },
  { label: 'Eastern', value: 'eastern' },
];

const PLANET_ORDER = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu'];

const SIGN_LORDS: Record<string, string> = {
  Aries: 'Mars',
  Taurus: 'Venus',
  Gemini: 'Mercury',
  Cancer: 'Moon',
  Leo: 'Sun',
  Virgo: 'Mercury',
  Libra: 'Venus',
  Scorpio: 'Mars',
  Sagittarius: 'Jupiter',
  Capricorn: 'Saturn',
  Aquarius: 'Saturn',
  Pisces: 'Jupiter',
};

const VIMSHOTTARI_SEQUENCE = [
  'Ketu',
  'Venus',
  'Sun',
  'Moon',
  'Mars',
  'Rahu',
  'Jupiter',
  'Saturn',
  'Mercury',
];

const VIMSHOTTARI_YEARS: Record<string, number> = {
  Ketu: 7,
  Venus: 20,
  Sun: 6,
  Moon: 10,
  Mars: 7,
  Rahu: 18,
  Jupiter: 16,
  Saturn: 19,
  Mercury: 17,
};

const NAKSHATRA_SPAN = 360 / 27;

function dash(value: unknown): string {
  return value === null || value === undefined || value === '' ? '—' : String(value);
}

function kpLord(longitude: number | undefined, depth: 1 | 2): string {
  if (longitude === undefined || Number.isNaN(longitude)) return '—';
  const normalized = ((longitude % 360) + 360) % 360;
  const nakIndex = Math.min(Math.floor((normalized * 27) / 360), 26);
  const degreeInNakshatra = normalized - nakIndex * NAKSHATRA_SPAN;
  const nakLord = VIMSHOTTARI_SEQUENCE[nakIndex % VIMSHOTTARI_SEQUENCE.length];
  let sequenceIndex = VIMSHOTTARI_SEQUENCE.indexOf(nakLord);
  let span = NAKSHATRA_SPAN;
  let offset = degreeInNakshatra;
  let lord = nakLord;

  for (let level = 0; level < depth; level++) {
    for (let i = 0; i < VIMSHOTTARI_SEQUENCE.length; i++) {
      const candidate = VIMSHOTTARI_SEQUENCE[(sequenceIndex + i) % VIMSHOTTARI_SEQUENCE.length];
      const candidateSpan = (span * VIMSHOTTARI_YEARS[candidate]) / 120;
      if (offset <= candidateSpan || i === VIMSHOTTARI_SEQUENCE.length - 1) {
        lord = candidate;
        sequenceIndex = VIMSHOTTARI_SEQUENCE.indexOf(candidate);
        span = candidateSpan;
        break;
      }
      offset -= candidateSpan;
    }
  }

  return lord;
}

@Component({
  selector: 'app-varga-charts-tab',
  imports: [FormsModule, Select, SelectButton, Skeleton, Tag, SectionCardComponent, KundliChartComponent],
  templateUrl: './varga-charts-tab.component.html',
  styleUrl: './varga-charts-tab.component.scss',
})
export class VargaChartsTabComponent {
  private store = inject(KundliStore);
  private vedicSvc = inject(VedicService);
  private prefs = inject(PreferencesService);

  protected readonly vargaOptions = VARGA_OPTIONS;
  protected readonly viewOptions = VIEW_OPTIONS;
  protected readonly styleOptions = STYLE_OPTIONS;
  protected readonly varga = signal('D1');
  protected readonly view = signal<ChartView>('both');
  protected readonly chartStyle = signal<KundliChartStyle>(this.prefs.chartStyle());

  protected readonly data = signal<VedicAll | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly loading = computed(() => !this.data() && !this.error());

  protected readonly currentVarga = computed<VargaChart | null>(() => {
    const v = this.data();
    return v?.vargas[this.varga()] ?? null;
  });
  protected readonly planetAnnotations = computed(() => this.data()?.planet_annotations ?? {});

  protected readonly rows = computed<VargaRow[]>(() => {
    const d = this.currentVarga();
    const natal = this.data()?.planets;
    if (!d || !natal) return [];
    return Object.entries(d.planets)
      .sort(([a], [b]) => {
        const ai = PLANET_ORDER.indexOf(a);
        const bi = PLANET_ORDER.indexOf(b);
        return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
      })
      .map(([planet, p]) => {
        const n = natal[planet];
        return {
          planet,
          glyph: planetGlyph(planet),
          degree: dash(n?.dms),
          rashi: p.sign,
          nakshatra: dash(n?.nakshatra),
          paada: n?.nakshatra_pada ?? '—',
          rashiLord: SIGN_LORDS[p.sign] ?? n?.sign_lord ?? '—',
          nakshatraLord: n?.nakshatra_lord ?? '—',
          subLord: kpLord(n?.longitude, 1),
          subSubLord: kpLord(n?.longitude, 2),
          vargottama: !!p.vargottama,
          retrograde: !!(p.retrograde ?? n?.retrograde),
        };
      });
  });

  protected readonly vargottamaCount = computed(() => this.rows().filter((row) => row.vargottama).length);

  constructor() {
    effect(() => {
      const id = this.store.activeId();
      this.data.set(null);
      this.error.set(null);
      if (!id) return;
      this.vedicSvc
        .all(id)
        .then((v) => this.data.set(v))
        .catch((e) => this.error.set((e as Error).message));
    });
  }

  protected onVargaChange(value: string): void {
    this.varga.set(value);
  }

  protected onViewChange(value: ChartView): void {
    this.view.set(value);
  }

  protected onStyleChange(value: KundliChartStyle): void {
    this.prefs.chartStyle.set(value);
    this.chartStyle.set(value);
  }

  protected chartStyleLabel(value: KundliChartStyle): string {
    if (value === 'south') return 'South Indian';
    if (value === 'north') return 'North Indian';
    return 'Eastern';
  }
}
