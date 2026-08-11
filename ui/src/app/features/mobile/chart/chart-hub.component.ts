import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ProfileSwitcherComponent } from '../profile-switcher/profile-switcher.component';
import { ProvenanceSheetComponent } from './provenance-sheet.component';
import { KundliChartComponent, KundliChartStyle } from '../../../shared/kundli-chart/kundli-chart.component';
import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';
import { DashaPayload, VargaChart, VedicAll } from '../../../core/models';
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
  queryParams?: Record<string, string>;
}

interface YantraTile {
  title: string;
  subtitle: string;
  tone: string;
  icon: string;
  route: string[];
  queryParams?: Record<string, string>;
  active?: boolean;
  featured?: boolean;
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
  imports: [KundliChartComponent, ProfileSwitcherComponent, ProvenanceSheetComponent, RouterLink],
  templateUrl: './chart-hub.component.html',
  styleUrl: './chart-hub.component.scss',
})
export class ChartHubComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  protected readonly preferences = inject(PreferencesService);
  protected readonly chart = signal<VedicAll | null>(null);
  protected readonly dashas = signal<DashaPayload | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly screenTitle = computed(() =>
    this.preferences.experienceMode() === 'guided' ? 'Your Story'
      : this.preferences.experienceMode() === 'practitioner' ? 'Yantra'
      : 'Explore',
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
  readonly sharedStyle = computed<KundliChartStyle>(() => this.preferences.chartStyle());

  /**
   * Glyph placements, as percentages of the frame, taken from the design's own
   * coordinates (node 46:154 at 160px). They are literal rather than derived
   * because the house anchors of an East Indian chart are fixed positions on
   * the grid, not something to recompute per reading — only *which* planets
   * land in them changes.
   */
  readonly cells = computed(() => this.adapter()?.cells ?? []);
  readonly rashiChart = computed<VargaChart | null>(() => {
    const chart = this.chart();
    if (!chart) return null;
    return chart.vargas?.['D1'] ?? this.rashiFallback(chart);
  });
  readonly provenanceRows = computed(() => this.adapter()?.provenance ?? []);

  /**
   * Routes are attached only where the screen exists. A card that navigates
   * nowhere is better than one that navigates somewhere wrong — the same rule
   * the remedies list follows for "View cancellation".
   */
  readonly explore = signal<ExploreCard[]>([
    {
      // First card on purpose. It is the one that answers "is this chart even
      // mine?", and it was previously reachable only three taps deep under a
      // section called Reference, which reads like a glossary.
      id: 'birth-details',
      title: 'Birth Details',
      subtitle: 'Lagna, rashi, nakshatra · place & ayanamsha',
      icon: 'explore-varga',
      route: ['/m', 'chart', 'birth-details'],
    },
    {
      id: 'varga',
      title: 'Charts & Vargas',
      subtitle: 'D1 plus divisional charts',
      icon: 'explore-varga',
      route: ['/m', 'chart', 'full'],
      queryParams: { varga: 'D9' },
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
      id: 'remedies',
      title: 'Remedies',
      subtitle: 'Practices active now',
      icon: 'remedy-rite',
      route: ['/m', 'remedies'],
    },
    {
      id: 'muhurta',
      title: 'Muhurthas',
      subtitle: 'Find better timing',
      icon: 'figma-yantra-calendar',
      route: ['/m', 'muhurta'],
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
  readonly advancedOpen = signal(false);
  readonly guidedCoreIds = ['remedies', 'muhurta', 'varga', 'yoga', 'transit', 'compat', 'readings'];
  readonly guidedAdvancedIds = ['dasha', 'strength', 'reference'];
  protected readonly visibleExplore = computed(() => {
    const cards = this.explore();
    if (this.preferences.experienceMode() === 'guided') {
      const allowed = this.advancedOpen()
        ? [...this.guidedCoreIds, ...this.guidedAdvancedIds]
        : this.guidedCoreIds;
      return cards.filter((card) => allowed.includes(card.id));
    }
    return cards;
  });

  protected readonly guidedStrengths = computed(() => {
    const angles = this.angles();
    const sun = angles.find((item) => item.label === 'SUN')?.sign ?? 'your Sun';
    const moon = angles.find((item) => item.label === 'MOON')?.sign ?? 'your Moon';
    const asc = angles.find((item) => item.label === 'ASCENDANT')?.sign ?? 'your rising sign';
    return [
      { label: 'How you shine', value: `${sun} Sun` },
      { label: 'How you feel', value: `${moon} Moon` },
      { label: 'How life meets you', value: `${asc} rising` },
    ];
  });

  protected readonly practitionerConfig = computed(() => {
    const chart = this.chart();
    return [
      chart?.meta?.ayanamsha?.name ?? 'Lahiri',
      `${this.preferences.nodeType() === 'true' ? 'True' : 'Mean'} Node`,
      chart?.provenance?.house_system ?? 'Whole-Sign',
      chart?.provenance?.timezone ?? chart?.meta?.place ?? 'Local time',
    ].join(' · ');
  });

  protected readonly dashaChain = computed(() => {
    const current = this.dashaData()?.current;
    return [
      { lord: current?.mahadasha?.lord, short: 'Mahā', active: false },
      { lord: current?.antardasha?.lord, short: 'Antar', active: false },
      { lord: current?.pratyantardasha?.lord, short: 'Prat', active: true },
      { lord: current?.sookshmadasha?.lord, short: 'Sookshma', active: false },
    ]
      .filter((row): row is { lord: string; short: string; active: boolean } => !!row.lord)
      .map((row) => ({ ...row, lord: this.shortLord(row.lord) }));
  });

  protected readonly dashaTiming = computed(() => {
    const current = this.dashaData()?.current;
    const pratyantar = current?.pratyantardasha;
    if (pratyantar?.end) return `${pratyantar.lord} Pratyantardasha until ${this.monthYear(pratyantar.end)}`;
    const antar = current?.antardasha;
    if (antar?.end) return `${antar.lord} Antardasha until ${this.monthYear(antar.end)}`;
    return 'Active period stack from Vimshottari dasha';
  });

  protected readonly yantraTiles = computed<YantraTile[]>(() => {
    const ascendant = this.angles().find((item) => item.label === 'ASCENDANT')?.sign ?? 'chart ready';
    const shadbala = this.chart()?.shadbala;
    const strongest = shadbala?.classical?.ranking?.[0];
    return [
      { title: 'Ask Siddha', subtitle: 'Grounded consultation from this chart', tone: 'accent', icon: 'nav-ask', route: ['/m', 'ask'], featured: true },
      { title: 'Charts & Vargas', subtitle: `D1-D60 · ${ascendant} Asc`, tone: 'accent', icon: 'figma-yantra-compass', route: ['/m', 'chart', 'full'], active: true },
      { title: 'Strength', subtitle: strongest ? `${strongest.planet} strongest` : 'Shadbala · AV', tone: 'good', icon: 'figma-yantra-activity', route: ['/m', 'chart', 'strength'] },
      { title: 'Yogas', subtitle: 'Strengths & cancellations', tone: 'warn', icon: 'figma-yantra-git-commit', route: ['/m', 'chart', 'yogas'] },
      { title: 'Transits', subtitle: 'Gochara · current sky', tone: 'warn', icon: 'figma-yantra-nav-map-pin', route: ['/m', 'transits'] },
      { title: 'Ashtakavarga', subtitle: 'SAV · BAV points', tone: 'muted', icon: 'figma-yantra-grid', route: ['/m', 'chart', 'strength'], queryParams: { tab: 'ashtakavarga' } },
      { title: 'Jaimini', subtitle: 'AK · AmK · padas', tone: 'muted', icon: 'figma-yantra-award', route: ['/m', 'chart', 'strength'], queryParams: { tab: 'jaimini' } },
      { title: 'Reference', subtitle: 'Avkahada · Ghatak · Fav', tone: 'muted', icon: 'figma-yantra-book-open', route: ['/m', 'chart', 'reference'] },
      { title: 'Compatibility', subtitle: 'Gun Milan matching', tone: 'muted', icon: 'figma-yantra-users', route: ['/m', 'compat'] },
      { title: 'Readings', subtitle: 'Latest predictions', tone: 'muted', icon: 'figma-yantra-file-text', route: ['/m', 'readings'] },
      { title: 'Notes', subtitle: `${this.noteCount()} notes`, tone: 'muted', icon: 'figma-yantra-edit-3', route: ['/m', 'notes'] },
      { title: 'Remedies', subtitle: 'Active practices', tone: 'good', icon: 'figma-yantra-sun', route: ['/m', 'remedies'] },
      { title: 'Muhurta', subtitle: 'Next windows', tone: 'warn', icon: 'figma-yantra-calendar', route: ['/m', 'muhurta'] },
    ];
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
        this.dashas.set(null);
        this.renderedChartId = null;
        this.loading.set(false);
        return;
      }
      const cached = this.vedic.cachedAll(activeId);
      if (cached) {
        this.chart.set(cached);
        this.dashas.set(cached.dashas ?? null);
        this.renderedChartId = activeId;
        this.loading.set(false);
        void this.refreshChart(activeId);
        void this.loadDashas(activeId);
        return;
      }
      if (this.renderedChartId !== activeId) this.loading.set(true);
      this.chart.set(await this.vedic.all(activeId));
      await this.loadDashas(activeId);
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
      if (!this.dashas()) this.dashas.set(chart.dashas ?? null);
    } catch {
      // Keep the saved chart visible when a background refresh fails.
    }
  }

  private dashaData(): DashaPayload | null {
    return this.dashas() ?? this.chart()?.dashas ?? null;
  }

  private async loadDashas(activeId: string): Promise<void> {
    if (this.preferences.experienceMode() !== 'practitioner') return;
    try {
      this.dashas.set(await this.vedic.dashas(activeId));
    } catch {
      this.dashas.set(this.chart()?.dashas ?? null);
    }
  }

  private shortLord(lord: string): string {
    const map: Record<string, string> = { Jupiter: 'Jup', Mercury: 'Merc', Venus: 'Ven', Saturn: 'Sat' };
    return map[lord] ?? lord;
  }

  private monthYear(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
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
