import { DecimalPipe } from '@angular/common';
import { Component, computed, effect, inject, signal } from '@angular/core';
import { AgGridAngular } from 'ag-grid-angular';
import { ColDef } from 'ag-grid-community';
import { SelectButton } from 'primeng/selectbutton';
import { FormsModule } from '@angular/forms';
import { LucideAngularModule } from 'lucide-angular';
import { Skeleton } from 'primeng/skeleton';
import { Tag } from 'primeng/tag';

import { DIGNITY_COLORS, planetGlyph } from '../../../core/glyphs';
import { KundliStore } from '../../../core/kundli.store';
import { VedicAll } from '../../../core/models';
import { ThemeService } from '../../../core/theme.service';
import { VedicService } from '../../../core/vedic.service';
import { DefListComponent, DefRow } from '../../../shared/def-list/def-list.component';
import { GlyphBadgeComponent } from '../../../shared/glyph-badge/glyph-badge.component';
import { darkGridTheme, lightGridTheme } from '../../../shared/grid-theme';
import { SectionCardComponent } from '../../../shared/section-card/section-card.component';

interface GrahaRow {
  planet: string;
  position: string;
  house: number;
  nakshatra: string;
  dignity: string;
  retrograde: boolean;
}

interface ShadbalaRow {
  planet: string;
  base: number;
  total: number;
  modifier: number;
  band: string;
  sthana: number;
  dig: number;
  kala: number;
  cheshta: number;
  naisargika: number;
  drik: number;
}

interface ConditionRow {
  planet: string;
  combustion: string;
  avastha: string;
  retrograde: string;
  war: string;
  modifier: number;
}

interface ClassicalRow {
  planet: string;
  sthana: number;
  dig: number;
  kala: number;
  cheshta: number;
  naisargika: number;
  drik: number;
  totalVirupas: number;
  rupas: number;
  requiredRupas: number;
  ratio: number;
  sufficient: boolean;
}

const VARGA_LIST = [
  'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10',
  'D11', 'D12', 'D16', 'D20', 'D24', 'D27', 'D30', 'D40', 'D45', 'D60',
];

@Component({
  selector: 'app-vedic-tab',
  imports: [
    AgGridAngular,
    DecimalPipe,
    FormsModule,
    LucideAngularModule,
    SelectButton,
    Skeleton,
    Tag,
    SectionCardComponent,
    DefListComponent,
    GlyphBadgeComponent,
  ],
  templateUrl: './vedic-tab.component.html',
  styleUrl: './vedic-tab.component.scss',
})
export class VedicTabComponent {
  private store = inject(KundliStore);
  private vedicSvc = inject(VedicService);
  private theme = inject(ThemeService);

  protected readonly kundli = this.store.active;
  protected readonly vargaOptions = VARGA_LIST;
  protected varga = 'D1';

  protected readonly data = signal<VedicAll | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly section = signal<'summary' | 'grahas' | 'strength' | 'vargas'>('summary');
  protected readonly loading = computed(() => !this.data() && !this.error());

  protected readonly gridTheme = computed(() =>
    this.theme.dark() ? darkGridTheme : lightGridTheme,
  );

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

  protected readonly meta = computed<DefRow[]>(() => {
    const v = this.data();
    if (!v) return [];
    const m = v.meta;
    return [
      { label: 'Date of birth', value: `${m.birth_date} · ${m.weekday}` },
      { label: 'Time of birth', value: m.birth_time },
      { label: 'Place', value: m.place || this.store.active()?.birth_city },
      { label: 'Lat / Long', value: `${m.latitude.toFixed(2)} · ${m.longitude.toFixed(2)}` },
      { label: 'Ayanamsha', value: `${m.ayanamsha.name} ${m.ayanamsha.dms}` },
      { label: 'Sidereal time', value: m.sidereal_time },
      { label: 'Local mean time', value: m.local_mean_time },
      { label: 'Node type', value: m.node_type },
    ];
  });

  protected readonly provenanceRows = computed<DefRow[]>(() => {
    const p = this.data()?.provenance;
    if (!p) return [];
    return [
      { label: 'Engine', value: p.engine },
      { label: 'Zodiac', value: p.zodiac },
      { label: 'House system', value: p.house_system },
      { label: 'Lagna method', value: p.lagna_method },
      { label: 'Timezone', value: p.timezone },
      { label: 'Position confidence', value: p.confidence['planetary_positions'] || 'computed' },
      { label: 'Varga confidence', value: p.confidence['vargas'] || 'mixed' },
      { label: 'Interpretation layer', value: p.confidence['yogas_doshas'] || 'rule-based' },
    ];
  });

  protected readonly trio = computed(() => {
    const a = this.data()?.avkahada;
    if (!a) return [];
    return [
      { label: 'Lagna', sign: a['lagna'], value: a['lagna'] },
      { label: 'Rashi (Moon)', sign: a['rashi'], value: a['rashi'] },
      { label: 'Nakshatra', sign: null, value: `${a['nakshatra']} · ${a['charan']}` },
    ];
  });

  protected readonly avkahada = computed<DefRow[]>(() => {
    const a = this.data()?.avkahada;
    if (!a) return [];
    return [
      { label: 'Lagna', value: a['lagna'] },
      { label: 'Lagna lord', value: a['lagna_lord'] },
      { label: 'Rashi', value: a['rashi'] },
      { label: 'Rashi lord', value: a['rashi_lord'] },
      { label: 'Nakshatra', value: a['nakshatra'] },
      { label: 'Nakshatra lord', value: a['nakshatra_lord'] },
      { label: 'Charan (pada)', value: a['charan'] },
      { label: 'Tithi', value: a['tithi'] },
      { label: 'Vara (day)', value: a['vara'] },
      { label: 'Paya', value: a['paya'], unverified: true },
      { label: 'Yoga', value: a['yoga'] },
      { label: 'Karana', value: a['karana'] },
      { label: 'Varna', value: a['varna'] },
      { label: 'Tatwa', value: a['tatwa'], unverified: true },
      { label: 'Vashya', value: a['vashya'], unverified: true },
      { label: 'Yoni', value: a['yoni'] },
      { label: 'Gana', value: a['gana'] },
      { label: 'Nadi', value: a['nadi'] },
      { label: 'Nadi pada', value: a['nadi_pada'], unverified: true },
      { label: 'Vihaga', value: a['vihaga'], unverified: true },
      { label: 'First letters', value: (a['first_letters'] || []).join(', ') },
      { label: 'Sun sign (Western)', value: a['sun_sign_western'] },
      { label: 'Decanate', value: a['decanate'] },
    ];
  });

  protected readonly ghatak = computed<DefRow[]>(() => {
    const g = this.data()?.ghatak;
    if (!g) return [];
    return [
      { label: 'Rashi', value: g['rashi'], unverified: true },
      { label: 'Month', value: g['month'], unverified: true },
      { label: 'Tithi', value: g['tithi'], unverified: true },
      { label: 'Day', value: g['day'], unverified: true },
      { label: 'Nakshatra', value: g['nakshatra'], unverified: true },
      { label: 'Lagna', value: g['lagna'], unverified: true },
      { label: 'Yoga', value: g['yoga'], unverified: true },
      { label: 'Karana', value: g['karana'], unverified: true },
      { label: 'Prahar', value: g['prahar'], unverified: true },
    ];
  });

  protected readonly favourable = computed<DefRow[]>(() => {
    const f = this.data()?.favourable;
    if (!f) return [];
    const join = (v: unknown) => (Array.isArray(v) ? v.join(', ') : (v as string));

    const rows: DefRow[] = [
      { label: 'Lucky number (birth date)', value: f['lucky_number'], hint: 'Numerology moolank — digital root of the birth day' },
    ];
    const astro = f['astrological_number'];
    if (astro) {
      rows.push({
        label: 'Lucky number (Lagna lord)',
        value: `${astro.number} · ${astro.planet}`,
        hint: astro.confirmed_by?.length
          ? `Also confirmed by: ${astro.confirmed_by.join(', ')}`
          : 'Ascendant ruler — the chart’s primary identity indicator',
      });
    }
    rows.push(
      { label: 'Good numbers', value: join(f['good_numbers']) },
      { label: 'Evil numbers', value: join(f['evil_numbers']) },
      { label: 'Good years', value: join(f['good_years']) },
      { label: 'Lucky days', value: join(f['lucky_days']) },
      { label: 'Good planets', value: join(f['good_planets']) },
      { label: 'Evil planets', value: join(f['evil_planets']) },
      { label: 'Yogakaraka', value: f['yogakaraka'] },
      { label: 'Friendly signs', value: join(f['friendly_signs']) },
      { label: 'Lucky metal', value: f['lucky_metal'] },
      { label: 'Lucky stone', value: f['lucky_stone'] },
      { label: 'Lucky direction', value: f['lucky_direction'] },
      { label: 'Lucky time', value: f['lucky_time'] },
    );
    const color = f['lucky_color'];
    if (color) {
      rows.push({ label: 'Lucky colour', value: color.name, swatch: color.hex, hint: color.source });
    }
    return rows;
  });

  protected readonly grahaRows = computed<GrahaRow[]>(() => {
    const v = this.data();
    if (!v) return [];
    return Object.entries(v.planets).map(([planet, p]) => ({
      planet,
      position: `${p.sign} ${p.dms}`,
      house: p.house,
      nakshatra: `${p.nakshatra} · p${p.nakshatra_pada}`,
      dignity: v.dignities[planet]?.dignity ?? '—',
      retrograde: !!p.retrograde,
    }));
  });

  protected readonly strongestGraha = computed(() => this.data()?.shadbala?.ranking?.[0] ?? null);

  protected readonly showV1 = signal(false);

  protected readonly classical = computed(() => {
    const c = this.data()?.shadbala?.classical;
    return c?.available ? c : null;
  });

  protected readonly classicalRows = computed<ClassicalRow[]>(() => {
    const c = this.classical();
    if (!c) return [];
    return c.ranking.map((rank) => {
      const row = c.rows[rank.planet];
      const comp = row.components;
      return {
        planet: rank.planet,
        sthana: comp['sthana_bala']?.virupas ?? 0,
        dig: comp['dig_bala']?.virupas ?? 0,
        kala: comp['kala_bala']?.virupas ?? 0,
        cheshta: comp['cheshta_bala']?.virupas ?? 0,
        naisargika: comp['naisargika_bala']?.virupas ?? 0,
        drik: comp['drik_bala']?.virupas ?? 0,
        totalVirupas: row.total_virupas,
        rupas: row.rupas,
        requiredRupas: row.required_rupas,
        ratio: row.ratio,
        sufficient: row.sufficient,
      };
    });
  });

  protected ratioWidth(ratio: number): number {
    // 1.0 = required minimum; scale so the bar caps at 2x required.
    return Math.max(4, Math.min(100, (ratio / 2) * 100));
  }

  protected readonly shadbalaRows = computed<ShadbalaRow[]>(() => {
    const shadbala = this.data()?.shadbala;
    if (!shadbala) return [];
    return shadbala.ranking.map((rank) => {
      const row = shadbala.rows[rank.planet];
      const c = row.components;
      return {
        planet: rank.planet,
        base: row.base_score ?? row.total_score,
        total: row.total_score,
        modifier: row.condition_modifier ?? 0,
        band: row.rank_band,
        sthana: c['sthana_bala']?.score ?? 0,
        dig: c['dig_bala']?.score ?? 0,
        kala: c['kala_bala']?.score ?? 0,
        cheshta: c['cheshta_bala']?.score ?? 0,
        naisargika: c['naisargika_bala']?.score ?? 0,
        drik: c['drik_bala']?.score ?? 0,
      };
    });
  });

  protected readonly conditionRows = computed<ConditionRow[]>(() => {
    const conditions = this.data()?.planetary_conditions ?? this.data()?.shadbala?.conditions;
    if (!conditions) return [];
    return Object.entries(conditions.rows).map(([planet, row]) => ({
      planet,
      combustion: row.combustion.active
        ? `${row.combustion.severity} (${row.combustion.orb}°)`
        : 'clear',
      avastha: row.avastha.name,
      retrograde: row.retrograde.active ? 'retrograde +' : 'direct',
      war: row.planetary_war.active ? row.planetary_war.role : 'none',
      modifier: row.net_modifier,
    }));
  });

  protected readonly grahaColumns: ColDef<GrahaRow>[] = [
    {
      field: 'planet',
      headerName: 'Graha',
      flex: 1.2,
      cellRenderer: (p: { value: string; data?: GrahaRow }) =>
        `<span class="cell-glyph">${planetGlyph(p.value)}</span> ${p.value}` +
        (p.data?.retrograde ? ' <span class="cell-retro">R</span>' : ''),
    },
    { field: 'position', headerName: 'Sign · Degree', flex: 1.4, cellClass: 'as-num' },
    {
      field: 'house',
      headerName: 'House',
      flex: 0.6,
      valueFormatter: (p) => `H${p.value}`,
      cellClass: 'as-num',
    },
    { field: 'nakshatra', headerName: 'Nakshatra', flex: 1.4 },
    {
      field: 'dignity',
      headerName: 'Dignity',
      flex: 1,
      cellStyle: (p) => ({ color: DIGNITY_COLORS[p.value as string] ?? 'var(--as-muted)' }),
    },
  ];

  protected readonly shadbalaColumns: ColDef<ShadbalaRow>[] = [
    {
      field: 'planet',
      headerName: 'Graha',
      flex: 1,
      cellRenderer: (p: { value: string }) => `<span class="cell-glyph">${planetGlyph(p.value)}</span> ${p.value}`,
    },
    {
      field: 'base',
      headerName: 'Base',
      flex: 0.7,
      cellClass: 'as-num',
    },
    {
      field: 'total',
      headerName: 'Adjusted',
      flex: 0.8,
      cellClass: 'as-num strength-total',
      valueFormatter: (p) => `${p.value}`,
    },
    { field: 'modifier', headerName: 'Mod', flex: 0.6, cellClass: 'as-num' },
    { field: 'band', headerName: 'Band', flex: 0.8 },
    { field: 'sthana', headerName: 'Sthana', flex: 0.8, cellClass: 'as-num' },
    { field: 'dig', headerName: 'Dig', flex: 0.7, cellClass: 'as-num' },
    { field: 'kala', headerName: 'Kala', flex: 0.7, cellClass: 'as-num' },
    { field: 'cheshta', headerName: 'Cheshta', flex: 0.8, cellClass: 'as-num' },
    { field: 'naisargika', headerName: 'Naisargika', flex: 0.9, cellClass: 'as-num' },
    { field: 'drik', headerName: 'Drik', flex: 0.7, cellClass: 'as-num' },
  ];

  protected readonly conditionColumns: ColDef<ConditionRow>[] = [
    {
      field: 'planet',
      headerName: 'Graha',
      flex: 1,
      cellRenderer: (p: { value: string }) => `<span class="cell-glyph">${planetGlyph(p.value)}</span> ${p.value}`,
    },
    { field: 'combustion', headerName: 'Combustion', flex: 1.1 },
    { field: 'avastha', headerName: 'Avastha', flex: 0.9 },
    { field: 'retrograde', headerName: 'Motion', flex: 0.9 },
    { field: 'war', headerName: 'War', flex: 0.8 },
    { field: 'modifier', headerName: 'Net mod', flex: 0.7, cellClass: 'as-num strength-total' },
  ];

  protected readonly currentVarga = computed(() => {
    const v = this.data();
    return v?.vargas[this.vargaKey()] ?? null;
  });

  private readonly vargaKey = signal('D1');

  protected onVargaChange(value: string): void {
    this.varga = value;
    this.vargaKey.set(value);
  }

  protected readonly vargaRows = computed(() => {
    const d = this.currentVarga();
    if (!d) return [];
    return Object.entries(d.planets).map(([planet, p]) => ({
      planet,
      glyph: planetGlyph(planet),
      sign: p.sign,
      house: p.house,
      vargottama: !!p.vargottama,
    }));
  });
}
