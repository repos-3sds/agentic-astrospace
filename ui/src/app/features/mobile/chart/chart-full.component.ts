import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { PlanetDetail, PlanetSheetComponent } from './planet-sheet.component';
import { KundliChartComponent, KundliChartStyle } from '../../../shared/kundli-chart/kundli-chart.component';
import { KundliStore } from '../../../core/kundli.store';
import { BhavaChalitPayload, VargaChart, VedicAll } from '../../../core/models';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { buildChartAdapter, PLANET_ABBR, PLANET_NAME, SIGN_ORDER } from './mobile-chart-data';

/** The three drawing conventions the app can render a chart in. */
export type ChartStyle = 'Eastern' | 'South' | 'North';

/**
 * Chart — full render (Figma node 36:86).
 *
 * Step two of the chart flow. The style toggle is the point of the screen: the
 * same chart drawn Eastern, South or North is three different-looking diagrams,
 * and which one a reader recognises depends entirely on where they learned. The
 * app should not decide that for them.
 *
 * Only occupied houses are tappable. An empty house has nothing to say, and a
 * sheet that opened to explain nothing would teach people that tapping is not
 * worth it.
 */
@Component({
  selector: 'as-chart-full',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [KundliChartComponent, PlanetSheetComponent, RouterLink],
  templateUrl: './chart-full.component.html',
  styleUrl: './chart-full.component.scss',
})
export class ChartFullComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly kundlis = inject(KundliStore);
  protected readonly preferences = inject(PreferencesService);
  private readonly vedic = inject(VedicService);
  readonly styles: ChartStyle[] = ['Eastern', 'South', 'North'];
  readonly vargas = ['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D16', 'D20', 'D24', 'D27', 'D30', 'D40', 'D45', 'D60'];
  readonly style = computed<ChartStyle>(() => this.toChartStyle(this.preferences.chartStyle()));
  readonly sharedStyle = computed<KundliChartStyle>(() => this.preferences.chartStyle());
  private readonly queryParams = toSignal(this.route.queryParamMap, { requireSync: true });
  readonly selectedVarga = signal('D1');
  protected readonly chart = signal<VedicAll | null>(null);
  protected readonly bhavaChalit = signal<BhavaChalitPayload | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly adapter = computed(() => {
    const chart = this.chart();
    return chart ? buildChartAdapter(chart, this.kundlis.active(), this.selectedVarga()) : null;
  });

  readonly cells = computed(() => this.adapter()?.cells ?? []);
  readonly selectedChart = computed<VargaChart | null>(() => {
    const chart = this.chart();
    if (!chart) return null;
    const vargaId = this.selectedVarga();
    return chart.vargas?.[vargaId] ?? (vargaId === 'D1' ? this.rashiFallback(chart) : null);
  });

  /** Expanded once, so the legend is not a second thing to decode. */
  readonly legend = computed(() => Object.entries(this.adapter()?.details ?? {}).map(([abbr, detail]) => ({
    abbr,
    name: PLANET_NAME[abbr] ?? detail.title.split(' in ')[0],
  })));

  readonly planetRows = computed(() => {
    const chart = this.chart();
    if (!chart) return [];
    const dignities = chart.dignities ?? {};
    return PLANET_SEQUENCE
      .filter((planet) => chart.planets?.[planet])
      .map((planet) => {
        const row = chart.planets[planet];
        return {
          planet,
          sign: row.sign ?? '—',
          degree: row.dms ?? (typeof row.degree_in_sign === 'number' ? `${row.degree_in_sign.toFixed(2)}°` : '—'),
          nakshatra: row.nakshatra ?? '—',
          pada: row.nakshatra_pada ?? '—',
          dignity: titleCase(dignities[planet]?.dignity) || '—',
          retrograde: row.retrograde ? 'R' : '—',
        };
      });
  });

  readonly houseLords = computed(() => {
    const chart = this.chart();
    if (!chart) return [];
    const varga = chart.vargas?.[this.selectedVarga()] ?? null;
    const ascendantSign = varga?.lagna?.sign ?? this.kundlis.active()?.ascendant ?? chart.avkahada?.['rashi'];
    const start = SIGN_ORDER.indexOf(ascendantSign);
    const houseSigns = start >= 0
      ? Array.from({ length: 12 }, (_, index) => SIGN_ORDER[(start + index) % SIGN_ORDER.length])
      : SIGN_ORDER.slice(0, 12);
    return houseSigns.map((sign, index) => ({
      house: index + 1,
      sign,
      lord: SIGN_LORD[sign] ?? '—',
    }));
  });

  readonly bhavaRows = computed(() => {
    if (this.selectedVarga() !== 'D1') return [];
    const chart = this.chart();
    const bhava = this.bhavaChalit();
    if (!chart || !bhava?.planets) return [];
    return PLANET_SEQUENCE
      .filter((planet) => chart.planets?.[planet] && bhava.planets?.[planet])
      .map((planet) => ({
        planet,
        whole: chart.planets[planet].house,
        sripati: bhava.planets[planet].house,
      }));
  });

  readonly selected = signal<PlanetDetail | null>(null);
  private renderedChartId: string | null = null;

  constructor() {
    if (this.route.snapshot.routeConfig?.path === 'chart/vargas') {
      this.selectedVarga.set('D9');
    }
    effect(() => {
      const requested = this.queryParams().get('varga')?.toUpperCase();
      if (requested && this.vargas.includes(requested)) {
        this.selectedVarga.set(requested);
      }
    });
    effect(() => {
      const activeId = this.kundlis.activeId();
      void this.load(activeId);
    });
  }

  protected retry(): void {
    void this.load(this.kundlis.activeId());
  }

  protected setStyle(style: ChartStyle): void {
    this.preferences.chartStyle.set(style.toLowerCase() as 'eastern' | 'south' | 'north');
  }

  protected setVarga(varga: string): void {
    this.selectedVarga.set(varga);
  }

  protected hasVarga(varga: string): boolean {
    if (varga === 'D1') return true;
    return !!this.chart()?.vargas?.[varga];
  }

  protected openPlanet(planet: string): void {
    const abbr = PLANET_ABBR[planet] ?? planet;
    const detail = this.adapter()?.details[abbr];
    if (detail) {
      this.selected.set(detail);
    }
  }

  protected openPlanetRow(planet: string): void {
    const abbr = PLANET_ABBR[planet] ?? planet.slice(0, 2);
    const detail = this.adapter()?.details[abbr];
    if (detail) this.selected.set(detail);
  }

  private async load(expectedActiveId: string | null): Promise<void> {
    this.error.set(null);
    try {
      await this.kundlis.load();
      const activeId = this.kundlis.activeId();
      if (expectedActiveId && activeId !== expectedActiveId) return;
      if (!activeId) {
        this.chart.set(null);
        this.bhavaChalit.set(null);
        this.renderedChartId = null;
        this.loading.set(false);
        return;
      }
      const cached = this.vedic.cachedAll(activeId);
      if (cached) {
        this.chart.set(cached);
        this.renderedChartId = activeId;
        this.loading.set(false);
        void this.loadBhavaChalit(activeId);
        void this.refreshChart(activeId);
        return;
      }
      if (this.renderedChartId !== activeId) this.loading.set(true);
      const [chart, bhavaChalit] = await Promise.all([
        this.vedic.all(activeId),
        this.vedic.bhavaChalit(activeId).catch(() => null),
      ]);
      this.chart.set(chart);
      this.bhavaChalit.set(bhavaChalit);
      this.renderedChartId = activeId;
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  private async refreshChart(activeId: string): Promise<void> {
    try {
      const chart = await this.vedic.refreshAll(activeId);
      if (this.kundlis.activeId() !== activeId) return;
      this.chart.set(chart);
      this.renderedChartId = activeId;
      void this.loadBhavaChalit(activeId);
    } catch {
      // Keep the saved chart visible when a background refresh fails.
    }
  }

  private async loadBhavaChalit(activeId: string): Promise<void> {
    try {
      const bhavaChalit = await this.vedic.bhavaChalit(activeId);
      if (this.kundlis.activeId() === activeId) this.bhavaChalit.set(bhavaChalit);
    } catch {
      if (this.kundlis.activeId() === activeId) this.bhavaChalit.set(null);
    }
  }

  private toChartStyle(style: 'eastern' | 'south' | 'north'): ChartStyle {
    return style === 'south' ? 'South' : style === 'north' ? 'North' : 'Eastern';
  }

  private rashiFallback(data: VedicAll): VargaChart | null {
    const lagnaSign = this.kundlis.active()?.ascendant ?? data.avkahada?.['rashi'];
    if (!lagnaSign) return null;
    return {
      name: 'Rāśi',
      signifies: 'Birth chart',
      verified_rule: true,
      lagna: { sign: lagnaSign },
      planets: Object.fromEntries(Object.entries(data.planets ?? {}).map(([planet, row]) => [
        planet,
        {
          sign: row.sign,
          house: row.house,
          retrograde: row.retrograde,
        },
      ])),
    };
  }
}

const PLANET_SEQUENCE = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu'];

const SIGN_LORD: Record<string, string> = {
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

function titleCase(value?: string): string {
  if (!value) return '';
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
