import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { EastChartComponent } from './east-chart.component';
import { ProfileSwitcherComponent } from '../profile-switcher/profile-switcher.component';
import { ProvenanceSheetComponent } from './provenance-sheet.component';
import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicAll } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { buildChartAdapter } from './mobile-chart-data';

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
  imports: [EastChartComponent, ProfileSwitcherComponent, ProvenanceSheetComponent, RouterLink],
  templateUrl: './chart-hub.component.html',
  styleUrl: './chart-hub.component.scss',
})
export class ChartHubComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  protected readonly preferences = inject(PreferencesService);
  protected readonly chart = signal<VedicAll | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly screenTitle = computed(() =>
    this.preferences.experienceMode() === 'guided' ? 'Your Story'
      : this.preferences.experienceMode() === 'practitioner' ? 'Chart Workbench'
      : 'Your Chart',
  );
  readonly profileName = computed(() => this.kundlis.active()?.name ?? 'Choose profile');
  readonly profileInitial = computed(() => this.profileName().slice(0, 1).toUpperCase());
  protected readonly adapter = computed(() => {
    const chart = this.chart();
    return chart ? buildChartAdapter(chart, this.kundlis.active()) : null;
  });
  readonly signature = computed(() => this.adapter()?.signature ?? {
    headline: 'Select a profile to compute your chart.',
    detail: 'Planet placements will load from your saved birth details.',
  });
  readonly angles = computed<AnglePoint[]>(() => this.adapter()?.angles ?? []);

  /** Which drawing convention the diagram uses — see EastChartComponent. */
  readonly chartStyleLabel = computed(() => {
    const style = this.preferences.chartStyle();
    return style === 'south' ? 'South' : style === 'north' ? 'North' : 'Eastern';
  });

  /**
   * Glyph placements, as percentages of the frame, taken from the design's own
   * coordinates (node 46:154 at 160px). They are literal rather than derived
   * because the house anchors of an East Indian chart are fixed positions on
   * the grid, not something to recompute per reading — only *which* planets
   * land in them changes.
   */
  readonly cells = computed(() => this.adapter()?.cells ?? []);
  readonly provenanceRows = computed(() => this.adapter()?.provenance ?? []);

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
      route: ['/m', 'chart', 'yogas'],
    },
    {
      id: 'strength',
      title: 'Strength & Advanced',
      subtitle: 'Shadbala, AV, Jaimini',
      icon: 'explore-strength',
      route: ['/m', 'chart', 'strength'],
    },
    {
      id: 'transit',
      title: 'Transits & Gochara',
      subtitle: 'What’s moving now',
      icon: 'explore-transit',
      route: ['/m', 'transits'],
    },
    {
      id: 'compat',
      title: 'Compatibility',
      subtitle: 'Gun Milan matching',
      icon: 'explore-compat',
      route: ['/m', 'compat'],
    },
    {
      id: 'readings',
      title: 'Readings',
      subtitle: 'Predictions & track record',
      icon: 'explore-readings',
      route: ['/m', 'readings'],
    },
    {
      id: 'reference',
      title: 'Reference',
      subtitle: 'Avkahada, tables, points',
      icon: 'explore-reference',
      route: ['/m', 'chart', 'reference'],
    },
  ]);

  readonly noteCount = signal(0);
  protected readonly visibleExplore = computed(() => {
    const cards = this.explore();
    if (this.preferences.experienceMode() === 'guided') {
      return cards.filter((card) => ['yoga', 'transit', 'compat', 'readings'].includes(card.id));
    }
    return cards;
  });

  /** The provenance sheet (36:247), shared with the full render. */
  readonly provenanceOpen = signal(false);
  readonly profileSwitcherOpen = signal(false);
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
}
