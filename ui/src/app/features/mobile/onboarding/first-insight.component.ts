import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { DashaPayload, VargaChart, VedicAll, birthTimeIsApproximate } from '../../../core/models';
import { BirthTimeBadgeComponent } from '../chart/birth-time-badge.component';
import { KundliChartComponent, KundliChartStyle } from '../../../shared/kundli-chart/kundli-chart.component';
import { buildChartAdapter, rashiFallback } from '../chart/mobile-chart-data';

/**
 * Traditional, hedged one-line associations for the day's strongest
 * (highest-Shadbala) planet — deliberately phrased as "a good day to", never
 * as a verdict about what will happen. Keeps the Guided variant's "one
 * action" grounded in the profile's real chart instead of generic filler.
 */
const STRENGTH_ACTION: Record<string, string> = {
  Sun: 'lead something small, in your own name',
  Moon: 'do one thing that genuinely comforts you',
  Mars: 'finish something you started weeks ago',
  Mercury: 'have the one conversation you have been putting off',
  Jupiter: 'teach, mentor, or make one generous decision',
  Venus: 'spend time on something beautiful, or with someone who matters',
  Saturn: 'commit to one small, unglamorous discipline',
  Rahu: 'take one calculated, ambitious step',
  Ketu: 'sit with one thing without needing to fix it',
};

/**
 * The first thing a new user sees after casting their chart (Figma nodes
 * 212:416 / 458 / 512 — "Aha, Guided/Balanced/Practitioner"). Previously this
 * screen read the real signed-in name but showed identical hardcoded chart
 * facts to every user; it now computes from the kundli birth-details just
 * created, same call `today.component.ts`'s prefetch makes
 * (`VedicService.all`), so what's shown here is the same chart the rest of
 * the app will use.
 */
@Component({
  selector: 'as-first-insight',
  standalone: true,
  imports: [RouterLink, KundliChartComponent, BirthTimeBadgeComponent],
  templateUrl: './first-insight.component.html',
  styleUrl: './first-insight.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'as-mobile' },
})
export class FirstInsightComponent {
  protected readonly preferences = inject(PreferencesService);
  protected readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);

  protected readonly name = computed(() => this.kundlis.active()?.name ?? '');
  protected readonly hasActiveProfile = computed(() => !!this.kundlis.activeId());
  protected readonly chart = signal<VedicAll | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  protected readonly adapter = computed(() => {
    const chart = this.chart();
    return chart ? buildChartAdapter(chart, this.kundlis.active()) : null;
  });

  protected readonly ahaMode = computed(() => this.preferences.experienceMode());

  protected readonly journeyCopy = computed(() => {
    const strength = this.strongest();
    const action = this.strengthAction();
    return {
      headline: 'Your cosmic guide is ready',
      lede: birthTimeIsApproximate(this.kundlis.active())
        ? 'We have calculated your cosmic footprint from an approximate birth time, so the rising sign and houses are our best estimate. Let us start aligning your days with your natural rhythm.'
        : 'We have calculated your unique cosmic footprint using your exact birth time. Let us start aligning your days with your natural rhythm.',
      strength: strength
        ? `You have ${this.strengthPhrase(strength.planet)}`
        : 'Your personal strengths are ready to explore',
      recommendation: action
        ? `Start with this: ${action}.`
        : 'Start gently today — choose one clear step and do it with attention.',
    };
  });

  /** Highest-Shadbala planet — the Guided variant's "one strength". */
  protected readonly strongest = computed(() => {
    const chart = this.chart();
    const top = chart?.shadbala?.classical?.ranking?.[0];
    if (!top) return null;
    return { planet: top.planet, sign: chart?.planets?.[top.planet]?.sign ?? '' };
  });

  protected readonly strengthAction = computed(() => {
    const planet = this.strongest()?.planet;
    return planet ? STRENGTH_ACTION[planet] ?? 'take one deliberate, unhurried step' : null;
  });

  // The style chosen one step earlier, which promised it "changes how charts are drawn".
  protected readonly practitionerStyle = computed<KundliChartStyle>(() => this.preferences.chartStyle());

  protected readonly practitionerChart = computed<VargaChart | null>(() => {
    const chart = this.chart();
    if (!chart) return null;
    return chart.vargas?.['D1'] ?? rashiFallback(chart);
  });

  protected readonly birthConstants = computed(() => {
    const chart = this.chart();
    return [
      chart?.meta?.ayanamsha?.name ?? 'Lahiri',
      `${this.preferences.nodeType() === 'true' ? 'True' : 'Mean'} Node`,
      chart?.provenance?.house_system ?? 'Whole-Sign',
      chart?.provenance?.timezone ?? chart?.meta?.place ?? 'Local time',
    ].join(' · ');
  });

  protected readonly dashaChain = computed(() => {
    const current = this.dashas()?.current;
    return [
      { lord: current?.mahadasha?.lord, short: 'Mahā' },
      { lord: current?.antardasha?.lord, short: 'Antar' },
      { lord: current?.pratyantardasha?.lord, short: 'Pratyantar' },
      { lord: current?.sookshmadasha?.lord, short: 'Sookshma', active: true },
    ]
      .filter((row): row is { lord: string; short: string; active?: boolean } => !!row.lord);
  });

  protected readonly birthMetrics = computed(() => {
    const chart = this.chart();
    const moon = chart?.planets?.['Moon'];
    const sun = chart?.planets?.['Sun'];
    // Sidereal lagna from the chart payload only. The profile's stored
    // `ascendant` is tropical and used to win here; the avkahada nakshatra is
    // the Moon's, so the lagna's own nakshatra comes from `lagna`.
    const lagnaDetails = chart?.lagna;
    const lagna = chart?.vargas?.['D1']?.lagna?.sign ?? lagnaDetails?.sign ?? chart?.avkahada?.['lagna'] ?? '—';
    const lagnaNakshatra = lagnaDetails?.nakshatra
      ? `${lagnaDetails.nakshatra}${lagnaDetails.nakshatra_pada ? ` ${lagnaDetails.nakshatra_pada}` : ''}`
      : undefined;
    return [
      { label: 'Lagna (Ascendant)', value: this.metricValue(lagna, lagnaNakshatra) },
      { label: 'Chandra (Moon)', value: this.planetMetric(moon) },
      { label: 'Surya (Sun)', value: this.planetMetric(sun) },
    ];
  });

  private readonly dashas = computed<DashaPayload | null>(() => this.chart()?.dashas ?? null);
  private profileLoadPromise: Promise<void> | null = null;

  constructor() {
    effect(() => {
      const id = this.kundlis.activeId();
      const loaded = this.kundlis.loaded();
      if (!loaded && !id) {
        void this.loadProfiles();
        return;
      }
      if (!id) {
        this.chart.set(null);
        this.error.set(null);
        this.loading.set(false);
        return;
      }
      void this.loadChart(id);
    });
  }

  private async loadChart(kundliId: string): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const cached = this.vedic.cachedAll(kundliId);
      const chart = cached ?? (await this.vedic.all(kundliId));
      this.chart.set(chart);
    } catch (e) {
      // The Aha moment is a bonus, not a gate — a failed fetch here must
      // never block a brand-new signup from reaching the app.
      this.error.set((e as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  private async loadProfiles(): Promise<void> {
    if (this.profileLoadPromise) return this.profileLoadPromise;
    this.loading.set(true);
    this.error.set(null);
    this.profileLoadPromise = this.kundlis.load().catch((error) => {
      this.error.set((error as Error).message);
      this.loading.set(false);
    }).finally(() => {
      this.profileLoadPromise = null;
    });
    return this.profileLoadPromise;
  }


  private strengthPhrase(planet: string): string {
    const phrases: Record<string, string> = {
      Sun: 'clear leadership and the courage to take responsibility',
      Moon: 'strong intuition and emotional intelligence',
      Mars: 'decisive energy and the will to finish what you start',
      Mercury: 'a sharp mind for learning, language, and practical choices',
      Jupiter: 'wisdom, generosity, and a natural guiding instinct',
      Venus: 'taste, harmony, and the ability to build beautiful connections',
      Saturn: 'discipline, patience, and the strength to stay with long work',
      Rahu: 'ambition, strategy, and comfort with unfamiliar paths',
      Ketu: 'inner detachment and the ability to see what is essential',
    };
    return phrases[planet] ?? `${planet} as a key support in your chart`;
  }

  private planetMetric(planet: { dms?: string; sign?: string; nakshatra?: string; nakshatra_pada?: number } | undefined): string {
    if (!planet) return '—';
    const nakshatra = planet.nakshatra
      ? ` (${planet.nakshatra}${planet.nakshatra_pada ? ` ${planet.nakshatra_pada}` : ''})`
      : '';
    return `${planet.dms ?? ''}${planet.dms ? ' ' : ''}${planet.sign ?? 'Unknown'}${nakshatra}`;
  }

  private metricValue(sign: string, nakshatra: string | undefined): string {
    return `${sign}${nakshatra ? ` (${nakshatra})` : ''}`;
  }
}
