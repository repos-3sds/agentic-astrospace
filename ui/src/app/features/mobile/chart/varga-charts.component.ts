import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  ViewChild,
  signal,
  computed,
  effect,
  inject,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { KundliChartComponent, KundliChartStyle } from '../../../shared/kundli-chart/kundli-chart.component';
import { KundliStore } from '../../../core/kundli.store';
import { VargaChart, VedicAll } from '../../../core/models';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { buildChartAdapter, PLANET_ABBR } from './mobile-chart-data';
import { PlanetDetail, PlanetSheetComponent } from './planet-sheet.component';

interface VargaOption {
  id: string;
  unverified?: boolean;
}

/**
 * Divisional charts (Figma node 39:87).
 *
 * D9 is the worked view in this node. The selector deliberately exposes the
 * complete engine-supported set rather than implying that "D1–D60" means
 * every integer. D5, D6, D8 and D11 carry the design's amber disclosure dot
 * because their rules await reference-chart verification.
 */
@Component({
  selector: 'as-varga-charts',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [KundliChartComponent, PlanetSheetComponent, RouterLink],
  templateUrl: './varga-charts.component.html',
  styleUrl: './varga-charts.component.scss',
})
export class VargaChartsComponent implements AfterViewInit {
  @ViewChild('vargaStrip') private readonly vargaStrip?: ElementRef<HTMLElement>;
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  protected readonly preferences = inject(PreferencesService);

  readonly selected = signal('D9');
  protected readonly data = signal<VedicAll | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly selectedPlanet = signal<PlanetDetail | null>(null);
  private renderedChartId: string | null = null;
  readonly vargas: VargaOption[] = [
    { id: 'D1' },
    { id: 'D2' },
    { id: 'D3' },
    { id: 'D4' },
    { id: 'D5', unverified: true },
    { id: 'D6', unverified: true },
    { id: 'D7' },
    { id: 'D8', unverified: true },
    { id: 'D9' },
    { id: 'D10' },
    { id: 'D11', unverified: true },
    { id: 'D12' },
    { id: 'D16' },
    { id: 'D20' },
    { id: 'D24' },
    { id: 'D27' },
    { id: 'D30' },
    { id: 'D40' },
    { id: 'D45' },
    { id: 'D60' },
  ];

  readonly chartStyle = computed<KundliChartStyle>(() => this.preferences.chartStyle());
  readonly selectedVarga = computed<VargaChart | null>(() => this.data()?.vargas?.[this.selected()] ?? null);
  readonly adapter = computed(() => {
    const data = this.data();
    return data ? buildChartAdapter(data, this.kundlis.active(), this.selected()) : null;
  });
  readonly chartTitle = computed(() => `${this.selected()} · ${this.selectedVarga()?.name ?? 'Divisional chart'}`);
  readonly chartMeaning = computed(() => this.selectedVarga()?.signifies ?? 'Computed divisional placements');
  readonly vargottama = computed(() =>
    Object.entries(this.selectedVarga()?.planets ?? {})
      .filter(([, row]) => row.vargottama)
      .map(([planet, row]) => `${planet} in ${row.sign}`),
  );

  constructor() {
    effect(() => {
      const activeId = this.kundlis.activeId();
      void this.load(activeId);
    });
  }

  ngAfterViewInit(): void {
    // The Figma frame is captured with D9 near the leading edge and the
    // neighbouring chips peeking at both edges. Re-establish that position on
    // every route entry.
    requestAnimationFrame(() => {
      const strip = this.vargaStrip?.nativeElement;
      const selected = strip?.querySelector<HTMLElement>('[aria-current="true"]');
      if (strip && selected) {
        // Node 39:87 leaves 55px before D9, with the tail of D8 visible.
        const currentLeft =
          selected.getBoundingClientRect().left - strip.getBoundingClientRect().left;
        strip.scrollLeft += currentLeft - 55;
      }
    });
  }

  protected chooseVarga(id: string): void {
    this.selected.set(id);
    this.selectedPlanet.set(null);
  }

  protected openPlanet(planet: string): void {
    const abbr = PLANET_ABBR[planet] ?? planet.slice(0, 2);
    const detail = this.adapter()?.details[abbr];
    if (detail) this.selectedPlanet.set(detail);
  }

  protected retry(): void {
    void this.load(this.kundlis.activeId());
  }

  private async load(expectedActiveId: string | null): Promise<void> {
    this.error.set(null);
    try {
      await this.kundlis.load();
      const activeId = this.kundlis.activeId();
      if (expectedActiveId && activeId !== expectedActiveId) return;
      if (!activeId) {
        this.data.set(null);
        this.renderedChartId = null;
        this.loading.set(false);
        return;
      }
      const cached = this.vedic.cachedAll(activeId);
      if (cached) {
        this.data.set(cached);
        this.renderedChartId = activeId;
        this.loading.set(false);
        void this.refreshChart(activeId);
        return;
      }
      if (this.renderedChartId !== activeId) this.loading.set(true);
      this.data.set(await this.vedic.all(activeId));
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
      this.data.set(chart);
      this.renderedChartId = activeId;
    } catch {
      // Keep the saved varga payload visible when background refresh fails.
    }
  }
}
