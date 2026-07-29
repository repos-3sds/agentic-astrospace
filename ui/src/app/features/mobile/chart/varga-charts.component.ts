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
import { EastChartComponent } from './east-chart.component';
import { KundliStore } from '../../../core/kundli.store';
import { VargaChart, VedicAll } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { buildChartAdapter } from './mobile-chart-data';

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
  imports: [EastChartComponent, RouterLink],
  templateUrl: './varga-charts.component.html',
  styleUrl: './varga-charts.component.scss',
})
export class VargaChartsComponent implements AfterViewInit {
  @ViewChild('vargaStrip') private readonly vargaStrip?: ElementRef<HTMLElement>;
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);

  readonly selected = signal('D9');
  protected readonly data = signal<VedicAll | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
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

  readonly chartCells = computed(() => {
    const data = this.data();
    return data ? buildChartAdapter(data, this.kundlis.active(), this.selected()).cells : [];
  });
  readonly selectedVarga = computed<VargaChart | null>(() => this.data()?.vargas?.[this.selected()] ?? null);
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
  }

  protected retry(): void {
    void this.load(this.kundlis.activeId());
  }

  private async load(expectedActiveId: string | null): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
      const activeId = this.kundlis.activeId();
      if (expectedActiveId && activeId !== expectedActiveId) return;
      if (!activeId) {
        this.data.set(null);
        return;
      }
      this.data.set(await this.vedic.all(activeId));
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }
}
