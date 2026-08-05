import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { DashaPayload, VargaChart, VedicAll } from '../../../core/models';
import { KundliChartComponent, KundliChartStyle } from '../../../shared/kundli-chart/kundli-chart.component';
import { buildChartAdapter } from '../chart/mobile-chart-data';

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
  imports: [RouterLink, KundliChartComponent],
  templateUrl: './first-insight.component.html',
  styleUrl: './first-insight.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'as-mobile' },
})
export class FirstInsightComponent {
  protected readonly preferences = inject(PreferencesService);
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);

  protected readonly name = computed(() => this.kundlis.active()?.name ?? '');
  protected readonly chart = signal<VedicAll | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  protected readonly adapter = computed(() => {
    const chart = this.chart();
    return chart ? buildChartAdapter(chart, this.kundlis.active()) : null;
  });

  protected readonly guidedLead = computed(() =>
    this.preferences.tone() === 'direct'
      ? 'Your strength is staying deliberate when other people rush.'
      : 'One of your strengths is staying thoughtful when other people rush.',
  );

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

  protected readonly sharedStyle = computed<KundliChartStyle>(() => this.preferences.chartStyle());

  protected readonly practitionerChart = computed<VargaChart | null>(() => {
    const chart = this.chart();
    if (!chart) return null;
    return chart.vargas?.['D1'] ?? this.rashiFallback(chart);
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
      { lord: current?.pratyantardasha?.lord, short: 'Prat', active: true },
    ]
      .filter((row): row is { lord: string; short: string; active?: boolean } => !!row.lord);
  });

  private readonly dashas = computed<DashaPayload | null>(() => this.chart()?.dashas ?? null);

  constructor() {
    effect(() => {
      const id = this.kundlis.activeId();
      if (!id) return;
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
        { sign: row.sign, house: row.house, retrograde: row.retrograde },
      ])),
    };
  }
}
