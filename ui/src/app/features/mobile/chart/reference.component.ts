import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { VedicService } from '../../../core/vedic.service';
import { AshtakavargaPayload, VedicAll } from '../../../core/models';
import { BackLinkDirective } from '../../../core/back-link.directive';

type ReferenceMode = 'home' | 'avkahada' | 'grahas' | 'ashtakavarga' | 'favourable';

/** One sign's row in the BAV/SAV matrix: each planet's bindus, then the SAV total. */
interface AshtaRow {
  sign: string;
  short: string;
  bindus: number[];
  sav: number;
}

const SIGN_SHORT: Record<string, string> = {
  Aries: 'Ari', Taurus: 'Tau', Gemini: 'Gem', Cancer: 'Can', Leo: 'Leo', Virgo: 'Vir',
  Libra: 'Lib', Scorpio: 'Sco', Sagittarius: 'Sag', Capricorn: 'Cap', Aquarius: 'Aqu', Pisces: 'Pis',
};

const PLANET_SHORT: Record<string, string> = {
  Sun: 'Su', Moon: 'Mo', Mars: 'Ma', Mercury: 'Me', Jupiter: 'Ju', Venus: 'Ve', Saturn: 'Sa',
};

interface ReferenceRow { label: string; value: string }
interface ReferenceSection { heading: string; note?: string; rows: ReferenceRow[]; tone?: 'caution' }

type Payload = Record<string, unknown>;

function text(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (Array.isArray(value)) return value.length ? value.map(text).join(', ') : '—';
  if (typeof value === 'object') {
    const named = value as { name?: unknown };
    return typeof named.name === 'string' ? named.name : JSON.stringify(value);
  }
  return String(value);
}

function rows(payload: Payload, fields: [key: string, label: string][]): ReferenceRow[] {
  return fields
    .filter(([key]) => payload[key] !== undefined && payload[key] !== null && payload[key] !== '')
    .map(([key, label]) => ({ label, value: text(payload[key]) }));
}

function withSanskrit(payload: Payload, key: string): string {
  const sanskrit = payload[`${key}_sanskrit`];
  return typeof sanskrit === 'string' && sanskrit ? `${text(payload[key])} (${sanskrit})` : text(payload[key]);
}

function avkahadaSections(avkahada: Payload, ghatak: Payload): ReferenceSection[] {
  const sections: ReferenceSection[] = [
    {
      heading: 'Chart anchors',
      rows: [
        ...(avkahada['lagna'] ? [{ label: 'Lagna (ascendant)', value: withSanskrit(avkahada, 'lagna') }] : []),
        ...rows(avkahada, [['lagna_lord', 'Lagna lord']]),
        ...(avkahada['rashi'] ? [{ label: 'Rashi (Moon sign)', value: withSanskrit(avkahada, 'rashi') }] : []),
        ...rows(avkahada, [['rashi_lord', 'Rashi lord'], ['nakshatra', 'Janma nakshatra'], ['nakshatra_lord', 'Nakshatra lord'], ['charan', 'Charan (pada)']]),
      ],
    },
    {
      heading: 'Birth constants',
      note: 'From the Moon’s nakshatra and sign — the matching points used in kundli milan.',
      rows: rows(avkahada, [
        ['varna', 'Varna'], ['vashya', 'Vashya'], ['yoni', 'Yoni'], ['gana', 'Gana'], ['nadi', 'Nadi'],
        ['nadi_pada', 'Nadi pada'], ['tatwa', 'Tatwa'], ['paya', 'Paya'], ['vihaga', 'Vihaga'],
      ]),
    },
    {
      heading: 'Panchanga at birth',
      rows: rows(avkahada, [['vara', 'Vara (weekday)'], ['tithi', 'Tithi'], ['yoga', 'Yoga'], ['karana', 'Karana']]),
    },
    {
      heading: 'Name and Western reference',
      rows: rows(avkahada, [
        ['name_letter', 'Name syllable (pada)'], ['first_letters', 'Nakshatra syllables'],
        ['sun_sign_western', 'Sun sign (Western, tropical)'], ['decanate', 'Decanate'],
      ]),
    },
    {
      heading: 'Ghatak chakra',
      tone: 'caution',
      note: 'Inauspicious markers keyed by your Moon sign — periods and points to treat with care, not your own birth values.',
      rows: [
        ...rows(ghatak, [['month', 'Ghatak month'], ['tithi', 'Ghatak tithis'], ['day', 'Ghatak weekday'], ['nakshatra', 'Ghatak nakshatra']]),
        ...(ghatak['lagna'] ? [{ label: 'Ghatak lagna', value: withSanskrit(ghatak, 'lagna') }] : []),
        ...(ghatak['rashi'] ? [{ label: 'Ghatak Moon sign', value: withSanskrit(ghatak, 'rashi') }] : []),
        ...rows(ghatak, [['yoga', 'Ghatak yoga'], ['karana', 'Ghatak karana'], ['prahar', 'Ghatak prahar']]),
      ],
    },
  ];
  return sections.filter((section) => section.rows.length);
}

function favourableSections(favourable: Payload): ReferenceSection[] {
  const astro = (favourable['astrological_number'] ?? null) as
    | { number?: number; planet?: string; source?: string; confirmed_by?: string[] }
    | null;
  const colour = favourable['lucky_color'] as { name?: string; planet?: string } | undefined;
  const sections: ReferenceSection[] = [
    {
      heading: 'Chart number',
      note: 'The number of the lagna lord, the ascendant’s ruler. This is the one shown on Today.',
      rows: astro?.number === undefined ? [] : [
        { label: 'Number', value: text(astro.number) },
        { label: 'From', value: astro.planet ? `${astro.planet}, the lagna lord` : text(astro.source) },
        ...(astro.confirmed_by?.length ? [{ label: 'Also agrees', value: astro.confirmed_by.join(', ') }] : []),
      ],
    },
    {
      heading: 'Numerology number (moolank)',
      note: 'A different method: the digital root of your birth day-of-month. Numerology, not the chart — so it can differ from the chart number.',
      rows: rows(favourable, [
        ['lucky_number', 'Moolank'], ['ruling_planet', 'Ruling planet'], ['good_numbers', 'Good numbers'],
        ['evil_numbers', 'Numbers to avoid'], ['good_years', 'Good years (ages)'],
      ]),
    },
    {
      heading: 'Lagna-lord signature',
      note: colour?.planet ? `Colour, metal, stone, direction and hora of ${colour.planet}, the lagna lord.` : undefined,
      rows: rows(favourable, [
        ['lucky_color', 'Colour'], ['lucky_metal', 'Metal'], ['lucky_stone', 'Stone'],
        ['lucky_direction', 'Direction'], ['lucky_time', 'Time'],
      ]),
    },
    {
      heading: 'Planets and signs',
      note: 'Functional benefics and malefics for your lagna; days and signs follow from them.',
      rows: rows(favourable, [
        ['good_planets', 'Supportive planets'], ['evil_planets', 'Planets to watch'], ['yogakaraka', 'Yogakaraka'],
        ['lucky_days', 'Supportive days'], ['friendly_signs', 'Friendly signs'],
      ]),
    },
  ];
  return sections.filter((section) => section.rows.length);
}

@Component({
  selector: 'as-chart-reference',
  standalone: true,
  imports: [BackLinkDirective, RouterLink],
  templateUrl: './reference.component.html',
  styleUrl: './reference.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReferenceComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  protected readonly mode = inject(ActivatedRoute).snapshot.data['referenceMode'] as ReferenceMode;
  protected readonly data = signal<VedicAll | null>(null);
  protected readonly ashtakavarga = signal<AshtakavargaPayload | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  protected readonly title = computed(() => ({
    home: 'Reference', avkahada: 'Avkahada chakra', grahas: 'Graha positions',
    ashtakavarga: 'Ashtakavarga tables', favourable: 'Favourable points',
  })[this.mode]);
  protected readonly subtitle = computed(() => ({
    home: 'Classical tables and birth constants — the practitioner’s workbench.',
    avkahada: 'Your birth constants, with the ghatak markers kept separate',
    grahas: 'Sidereal positions, nakshatra-pada and conditions',
    ashtakavarga: 'Bindu tables computed from your chart',
    favourable: 'Two number conventions and the lagna-lord signature — steady across your life.',
  })[this.mode]);
  protected readonly homeCards = [
    { label: 'Avkahada & Ghatak', detail: 'Varna, vashya, yoni, gana, nadi, tatwa · ghatak points', route: 'avkahada' },
    { label: 'Graha positions & conditions', detail: 'Degrees, nakshatra-pada, dignity and motion', route: 'grahas' },
    { label: 'Ashtakavarga tables', detail: 'Planet and sign bindu working', route: 'ashtakavarga' },
    { label: 'Favourable points', detail: 'Birth-constant colours, numbers and directions', route: 'favourable' },
  ];

  /**
   * Avkahada, ghatak and favourable points as labelled sections. Until
   * 2026-10-15 this screen spread `{...avkahada, ...ghatak}` into one flat
   * key dump, so the ghatak lagna/rashi/nakshatra/tithi — the *inauspicious*
   * markers keyed by the Moon sign — overwrote the person's own constants
   * and were shown as theirs.
   */
  protected readonly sections = computed<ReferenceSection[]>(() => {
    const data = this.data();
    if (!data) return [];
    if (this.mode === 'avkahada') return avkahadaSections(data.avkahada ?? {}, data.ghatak ?? {});
    if (this.mode === 'favourable') return favourableSections(data.favourable ?? {});
    return [];
  });
  protected readonly planets = computed(() => Object.entries(this.data()?.planets ?? {}));

  /**
   * Ashtakavarga as the classical matrix: one row per sign, one column per
   * contributing planet (Sun through Saturn), SAV at the end. Until
   * 2026-10-15 this screen flattened the raw payload into "bav · Sun · 0 = 4"
   * rows and never showed a table.
   */
  protected readonly ashtaPlanets = computed(() => this.ashtakavarga()?.planets ?? []);
  protected readonly ashtaPlanetShort = computed(() => this.ashtaPlanets().map((planet) => PLANET_SHORT[planet] ?? planet.slice(0, 2)));
  protected readonly ashtaRows = computed<AshtaRow[]>(() => {
    const data = this.ashtakavarga();
    if (!data?.signs?.length) return [];
    return data.signs.map((row) => ({
      sign: row.sign,
      short: SIGN_SHORT[row.sign] ?? row.sign.slice(0, 3),
      bindus: data.planets.map((planet) => row.bav[planet] ?? 0),
      sav: row.sav,
    }));
  });
  protected readonly ashtaTotals = computed(() => {
    const data = this.ashtakavarga();
    if (!data) return null;
    return { bav: data.planets.map((planet) => data.totals.bav[planet] ?? 0), sav: data.totals.sav };
  });
  /** The classical SAV total is always 337, so "337 of 337" said nothing
   * (U26). How many signs reach the supportive 28 bindus differs per chart. */
  protected readonly ashtaSupportive = computed(() => this.ashtaRows().filter((row) => row.sav >= 28).length);
  protected readonly ashtaStrongest = computed(() => [...this.ashtaRows()].sort((a, b) => b.sav - a.sav).slice(0, 3));
  protected readonly ashtaWeakest = computed(() => [...this.ashtaRows()].sort((a, b) => a.sav - b.sav).slice(0, 3));
  protected readonly ashtaPinda = computed(() => this.ashtakavarga()?.pinda_rank ?? []);

  constructor() { if (this.mode !== 'home') void this.load(); else this.loading.set(false); }

  protected async load(): Promise<void> {
    this.loading.set(true); this.error.set(null);
    try {
      await this.kundlis.load();
      const profile = this.kundlis.active();
      if (!profile) throw new Error('Select a profile to open reference tables.');
      if (this.mode === 'ashtakavarga') {
        this.ashtakavarga.set(await this.vedic.ashtakavarga(profile.id));
      } else {
        this.data.set(await this.vedic.all(profile.id));
      }
    } catch (error) {
      this.error.set((error as Error).message);
    } finally { this.loading.set(false); }
  }

  /** 0..1 heat for a SAV cell: 28 is the classical neutral mark, 18..40 the usual spread. */
  protected savHeat(sav: number): number {
    return Math.min(1, Math.max(0, (sav - 18) / 22));
  }
}
