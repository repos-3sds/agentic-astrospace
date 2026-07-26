import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ChartCell, EastChartComponent } from './east-chart.component';
import { ProvenanceSheetComponent } from './provenance-sheet.component';

/** One of the three placements the hub leads with. */
export interface AnglePoint {
  label: string;
  sign: string;
  degree: string;
}

/** A deeper area of the chart, reachable from the hub. */
export interface ExploreCard {
  id: string;
  title: string;
  subtitle: string;
  icon: string;
  /** Present once the destination exists; absent leaves the card inert. */
  route?: string[];
}

/**
 * Chart Hub (Figma node 35:57) — the Chart tab's home and the entry to the
 * chart flow: hub, full render, planet detail, provenance.
 *
 * The order is the argument. A plain-language signature comes first, then the
 * three placements most people actually know, then the diagram, and only then
 * the eight specialist areas. Someone who has never read a chart gets a
 * sentence; someone who reads charts for a living gets Shadbala and Jaimini —
 * without either one wading through the other.
 *
 * The provenance row is not a footer. It sits directly under the diagram
 * because that is where "where did this come from" gets asked, and Epic J
 * requires the answer be one tap away rather than buried in settings.
 */
@Component({
  selector: 'as-chart-hub',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [EastChartComponent, ProvenanceSheetComponent, RouterLink],
  templateUrl: './chart-hub.component.html',
  styleUrl: './chart-hub.component.scss',
})
export class ChartHubComponent {
  readonly profileName = signal('Lakshmi');
  readonly profileInitial = signal('L');

  readonly signature = signal({
    headline: 'Warm, communicative, and grounded once you commit.',
    detail: 'Gemini Sun · Cancer Moon · Taurus rising — the detail is just below.',
  });

  readonly angles = signal<AnglePoint[]>([
    { label: 'SUN', sign: 'Gemini', degree: '23° 14’' },
    { label: 'MOON', sign: 'Cancer', degree: '04° 51’' },
    { label: 'ASCENDANT', sign: 'Taurus', degree: '11° 02’' },
  ]);

  /** Which drawing convention the diagram uses — see EastChartComponent. */
  readonly chartStyle = signal('Eastern');

  /**
   * Glyph placements, as percentages of the frame, taken from the design's own
   * coordinates (node 46:154 at 160px). They are literal rather than derived
   * because the house anchors of an East Indian chart are fixed positions on
   * the grid, not something to recompute per reading — only *which* planets
   * land in them changes.
   */
  readonly cells = signal<ChartCell[]>([
    { planets: 'Su·Me', x: 67.6, y: 5.9 },
    { planets: 'As·Ve', x: 41.9, y: 12.6 },
    { planets: 'Ke', x: 18.9, y: 6.6 },
    { planets: 'Mo', x: 86.0, y: 21.9 },
    { planets: 'Ju', x: 13.2, y: 45.9 },
    { planets: 'Sa', x: 87.9, y: 71.9 },
    { planets: 'Ma', x: 45.6, y: 79.3 },
    { planets: 'Ra', x: 19.6, y: 87.6 },
    { sign: 'Ar', x: 6.9, y: 20.25 },
    { sign: 'Le', x: 80.2, y: 46.25 },
    { sign: 'Cp', x: 20.25, y: 72.25 },
    { sign: 'Li', x: 73.8, y: 86.9 },
  ]);

  /**
   * Routes are attached only where the screen exists. A card that navigates
   * nowhere is better than one that navigates somewhere wrong — the same rule
   * the remedies list follows for "View cancellation".
   */
  readonly explore = signal<ExploreCard[]>([
    {
      id: 'varga',
      title: 'Divisional charts',
      subtitle: 'D1–D60, all varga',
      icon: 'explore-varga',
      route: ['/m', 'chart', 'vargas'],
    },
    {
      id: 'dasha',
      title: 'Life Periods',
      subtitle: 'Dashas & Yogini',
      icon: 'explore-dasha',
      route: ['/m', 'chart', 'periods'],
    },
    {
      id: 'yoga',
      title: 'Yogas & Doshas',
      subtitle: 'Strengths & flags',
      icon: 'explore-yoga',
    },
    {
      id: 'strength',
      title: 'Strength & Advanced',
      subtitle: 'Shadbala, AV, Jaimini',
      icon: 'explore-strength',
    },
    {
      id: 'transit',
      title: 'Transits & Gochara',
      subtitle: 'What’s moving now',
      icon: 'explore-transit',
    },
    {
      id: 'compat',
      title: 'Compatibility',
      subtitle: 'Gun Milan matching',
      icon: 'explore-compat',
    },
    {
      id: 'readings',
      title: 'Readings',
      subtitle: 'Predictions & track record',
      icon: 'explore-readings',
    },
    {
      id: 'reference',
      title: 'Reference',
      subtitle: 'Avkahada, tables, points',
      icon: 'explore-reference',
    },
  ]);

  readonly noteCount = signal(3);

  /** The provenance sheet (36:247), shared with the full render. */
  readonly provenanceOpen = signal(false);
}
