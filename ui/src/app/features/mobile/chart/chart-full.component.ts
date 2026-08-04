import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { EastChartComponent, PlanetSelection } from './east-chart.component';
import { PlanetDetail, PlanetSheetComponent } from './planet-sheet.component';
import { RegionalChartComponent } from './regional-chart.component';
import { KundliStore } from '../../../core/kundli.store';
import { VedicAll } from '../../../core/models';
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
  imports: [EastChartComponent, PlanetSheetComponent, RegionalChartComponent, RouterLink],
  templateUrl: './chart-full.component.html',
  styleUrl: './chart-full.component.scss',
})
export class ChartFullComponent {
  private readonly kundlis = inject(KundliStore);
  protected readonly preferences = inject(PreferencesService);
  private readonly vedic = inject(VedicService);
  readonly styles: ChartStyle[] = ['Eastern', 'South', 'North'];
  readonly vargas = ['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D16', 'D20', 'D24', 'D27', 'D30', 'D40', 'D45', 'D60'];
  readonly style = signal<ChartStyle>(this.toChartStyle(this.preferences.chartStyle()));
  readonly selectedVarga = signal('D9');
  protected readonly chart = signal<VedicAll | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly adapter = computed(() => {
    const chart = this.chart();
    return chart ? buildChartAdapter(chart, this.kundlis.active(), this.selectedVarga()) : null;
  });

  readonly cells = computed(() => this.adapter()?.cells ?? []);

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

  readonly selected = signal<PlanetDetail | null>(null);
  private renderedChartId: string | null = null;

  constructor() {
    effect(() => {
      const activeId = this.kundlis.activeId();
      void this.load(activeId);
    });
  }

  protected retry(): void {
    void this.load(this.kundlis.activeId());
  }

  protected setStyle(style: ChartStyle): void {
    this.style.set(style);
    this.preferences.chartStyle.set(style.toLowerCase() as 'eastern' | 'south' | 'north');
  }

  protected setVarga(varga: string): void {
    this.selectedVarga.set(varga);
  }

  protected hasVarga(varga: string): boolean {
    if (varga === 'D1') return true;
    return !!this.chart()?.vargas?.[varga];
  }

  protected openPlanet(selection: PlanetSelection): void {
    const detail = this.adapter()?.details[selection.planet];
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
        this.renderedChartId = null;
        this.loading.set(false);
        return;
      }
      const cached = this.vedic.cachedAll(activeId);
      if (cached) {
        this.chart.set(cached);
        this.renderedChartId = activeId;
        this.loading.set(false);
        return;
      }
      if (this.renderedChartId !== activeId) this.loading.set(true);
      this.chart.set(await this.vedic.all(activeId));
      this.renderedChartId = activeId;
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  private toChartStyle(style: 'eastern' | 'south' | 'north'): ChartStyle {
    return style === 'south' ? 'South' : style === 'north' ? 'North' : 'Eastern';
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
