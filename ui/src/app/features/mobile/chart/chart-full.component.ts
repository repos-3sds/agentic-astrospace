import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { EastChartComponent, PlanetSelection } from './east-chart.component';
import { PlanetDetail, PlanetSheetComponent } from './planet-sheet.component';
import { RegionalChartComponent } from './regional-chart.component';
import { KundliStore } from '../../../core/kundli.store';
import { VedicAll } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { buildChartAdapter, PLANET_NAME } from './mobile-chart-data';

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
  private readonly vedic = inject(VedicService);
  readonly styles: ChartStyle[] = ['Eastern', 'South', 'North'];
  readonly style = signal<ChartStyle>('Eastern');
  protected readonly chart = signal<VedicAll | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly adapter = computed(() => {
    const chart = this.chart();
    return chart ? buildChartAdapter(chart, this.kundlis.active()) : null;
  });

  readonly cells = computed(() => this.adapter()?.cells ?? []);

  /** Expanded once, so the legend is not a second thing to decode. */
  readonly legend = computed(() => Object.entries(this.adapter()?.details ?? {}).map(([abbr, detail]) => ({
    abbr,
    name: PLANET_NAME[abbr] ?? detail.title.split(' in ')[0],
  })));

  readonly selected = signal<PlanetDetail | null>(null);

  constructor() {
    effect(() => {
      const activeId = this.kundlis.activeId();
      void this.load(activeId);
    });
  }

  protected retry(): void {
    void this.load(this.kundlis.activeId());
  }

  protected openPlanet(selection: PlanetSelection): void {
    const detail = this.adapter()?.details[selection.planet];
    if (detail) {
      this.selected.set(detail);
    }
  }

  private async load(expectedActiveId: string | null): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
      const activeId = this.kundlis.activeId();
      if (expectedActiveId && activeId !== expectedActiveId) return;
      if (!activeId) {
        this.chart.set(null);
        return;
      }
      this.chart.set(await this.vedic.all(activeId));
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }
}
