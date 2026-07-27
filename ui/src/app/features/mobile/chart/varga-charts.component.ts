import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  ViewChild,
  signal,
  computed,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { ChartCell, EastChartComponent } from './east-chart.component';

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

  readonly selected = signal('D9');
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

  /** Positions are the literal anchors from the Figma D9 chart. */
  readonly cells = signal<ChartCell[]>([
    { sign: 'Ta', planets: 'Ve · Me', x: 44.21, y: 9.4 },
    { sign: 'Le', planets: 'As', x: 83.92, y: 45.4 },
    { sign: 'Sc', x: 48.07, y: 83.92 },
    { sign: 'Aq', planets: 'Sa', x: 11.92, y: 45.4 },
    { sign: 'Pi', x: 21.33, y: 8.59 },
    { sign: 'Ar', planets: 'Ma', x: 7.48, y: 19.4 },
    { sign: 'Ge', planets: 'Ke', x: 74.59, y: 5.4 },
    { sign: 'Cn', planets: 'Su', x: 87.92, y: 20.4 },
    { sign: 'Vi', x: 90.18, y: 73.92 },
    { sign: 'Li', planets: 'Mo', x: 73.48, y: 86.07 },
    { sign: 'Sg', planets: 'Ju · Ra', x: 18.14, y: 87.07 },
    { sign: 'Cp', x: 7.92, y: 74.59 },
  ]);
  readonly chartCells = computed(() => {
    if (this.selected() === 'D1') {
      return [
        { sign: 'Ta', planets: 'As · Ve', x: 44.5, y: 9.4 }, { sign: 'Ge', planets: 'Su · Me', x: 70.9, y: 5.4 },
        { sign: 'Cn', planets: 'Mo', x: 87.5, y: 20.4 }, { sign: 'Le', x: 84.2, y: 47.9 },
        { sign: 'Vi', planets: 'Sa', x: 89.6, y: 71.4 }, { sign: 'Li', x: 74.7, y: 88.6 },
        { sign: 'Sc', planets: 'Ma', x: 47.5, y: 81.4 }, { sign: 'Sg', planets: 'Ra', x: 21.3, y: 87.1 },
        { sign: 'Cp', planets: 'Ju', x: 7.9, y: 72.1 }, { sign: 'Aq', x: 11.9, y: 47.9 },
        { sign: 'Pi', planets: 'Ke', x: 20.6, y: 6.1 }, { sign: 'Ar', x: 8.4, y: 21.9 },
      ];
    }
    if (this.selected() === 'D10') {
      return this.cells().map((cell, index) => ({ ...cell, planets: index % 3 === 0 ? cell.planets : cell.planets }));
    }
    return this.cells();
  });
  readonly chartTitle = computed(() => this.selected() === 'D1' ? 'D1 · RĀŚI' : this.selected() === 'D10' ? 'D10 · DAŚĀṂŚA' : 'D9 · NAVAMSHA');
  readonly chartMeaning = computed(() => this.selected() === 'D1' ? 'Self & life path' : this.selected() === 'D10' ? 'Career & public work' : 'Marriage & dharma');

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
}
