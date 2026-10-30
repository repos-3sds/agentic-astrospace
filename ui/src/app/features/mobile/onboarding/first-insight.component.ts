import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { EmailSettingsService } from '../../../core/email-settings.service';
import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';
import { PushService } from '../../../core/push.service';
import { VedicService } from '../../../core/vedic.service';
import { DashaPeriod, LifeStory, VargaChart, VedicAll } from '../../../core/models';
import { ThemeService } from '../../../core/theme.service';
import { SplashComponent } from '../../../shell/splash/splash.component';
import { BirthTimeBadgeComponent } from '../chart/birth-time-badge.component';
import { KundliChartComponent, KundliChartStyle } from '../../../shared/kundli-chart/kundli-chart.component';
import { rashiFallback } from '../chart/mobile-chart-data';
import { queueTodayTips } from '../today/first-visit-tips.component';

/** How long "Reading your chart" stays up, at the least. */
const CAST_MS = 3000;

/**
 * The reveal at the end of setup: "your chart in three lines" (onboarding
 * plan 2026-10-30, approved by Hawk). The story's headline, then the rising
 * sign, the Moon and the running period, each with one plain line from the
 * same story Explore › Your story tells. Practitioners also get the D1 in the
 * style they just picked.
 *
 * This is also where the morning reading is offered: notifications are asked
 * here, with a reason, instead of the system popup firing over the birth
 * details form (PushService skips its launch question during setup), and the
 * email copy is a switch that starts off.
 */
@Component({
  selector: 'as-first-insight',
  standalone: true,
  imports: [RouterLink, KundliChartComponent, BirthTimeBadgeComponent, SplashComponent],
  templateUrl: './first-insight.component.html',
  styleUrl: './first-insight.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'as-mobile' },
})
export class FirstInsightComponent {
  protected readonly preferences = inject(PreferencesService);
  protected readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  private readonly push = inject(PushService);
  private readonly emailSettings = inject(EmailSettingsService);
  private readonly router = inject(Router);
  protected readonly theme = inject(ThemeService);

  protected readonly chart = signal<VedicAll | null>(null);
  protected readonly story = signal<LifeStory | null>(null);
  private readonly mahadasha = signal<DashaPeriod | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly emailToo = signal(false);
  protected readonly finishing = signal(false);

  /**
   * "Reading your chart": a short moment, at least three seconds, while four
   * real steps tick off (onboarding plan 2026-10-30). The chart was started
   * on birth details, so this is usually all the wait there is.
   */
  protected readonly castSteps = [
    'Placing the nine grahas',
    'Finding your rising sign',
    'Finding your Moon’s nakshatra',
    'Opening your current chapter',
  ];
  protected readonly castStep = signal(0);
  private readonly castShown = signal(false);
  protected readonly casting = computed(() => this.loading() || !this.castShown());

  protected readonly name = computed(() => this.kundlis.active()?.name ?? '');
  protected readonly hasActiveProfile = computed(() => !!this.kundlis.activeId());
  protected readonly ahaMode = computed(() => this.preferences.experienceMode());

  /** The story's own headline ("Quick to act, fair at heart."), the same words Explore › Your story opens with. */
  protected readonly headline = computed(() => this.story()?.headline ?? 'Your chart is ready');

  /**
   * Only ask where the answer is still open. On the web there is nothing to
   * ask, and a reader who already said yes (a second profile, a reinstall)
   * should not be offered it again.
   */
  protected readonly askNotifications = computed(() => this.push.permission() === 'prompt');

  /** Rising sign, Moon, and the running period: three facts, each with one plain line. */
  protected readonly facts = computed(() => {
    const chart = this.chart();
    const lines = this.story()?.traits ?? [];
    const lagna = chart?.lagna;
    const moon = chart?.planets?.['Moon'];
    const maha = this.mahadasha();
    const until = maha?.end ? new Date(maha.end).getFullYear() : null;
    const rows = [
      {
        label: 'HOW YOU MEET THE WORLD',
        name: `${lagna?.sign ?? '—'} rising`,
        line: lines[0]?.detail ?? '',
        term: lagna ? `Lagna · ${lagna.sign}${lagna.nakshatra ? ` · ${lagna.nakshatra} ${lagna.nakshatra_pada ?? ''}` : ''}` : '',
      },
      {
        label: 'YOUR MIND AND HEART',
        name: `Moon in ${moon?.sign ?? '—'}`,
        line: lines[2]?.detail ?? '',
        term: moon ? `Chandra · ${moon.dms ?? ''} ${moon.sign}${moon.nakshatra ? ` · ${moon.nakshatra} ${moon.nakshatra_pada ?? ''}` : ''}` : '',
      },
      {
        label: 'THE CHAPTER YOU ARE IN',
        name: maha ? `${maha.lord} period${until ? `, until ${until}` : ''}` : 'Your current period',
        // The chapter opens by naming the period, which the row title already says.
        line: (this.story()?.chapter ?? '').replace(/^You are in an? \w+ period until \d{4}\. /, ''),
        term: maha ? `Vimshottari Mahadasha · ${maha.lord}` : '',
      },
    ];
    return rows.filter((r) => r.line);
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

  private profileLoadPromise: Promise<void> | null = null;

  constructor() {
    void this.push.refreshPermission();
    const tick = setInterval(() => {
      if (this.castStep() < this.castSteps.length) this.castStep.update((n) => n + 1);
    }, CAST_MS / (this.castSteps.length + 1));
    setTimeout(() => {
      clearInterval(tick);
      this.castStep.set(this.castSteps.length);
      this.castShown.set(true);
    }, CAST_MS);
    inject(DestroyRef).onDestroy(() => clearInterval(tick));
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

  protected toggleEmail(): void {
    this.emailToo.update((on) => !on);
  }

  /**
   * "Open Today", with the morning reading turned on when the reader asked
   * for it. The system question is the reader's answer; whatever they say,
   * Today opens. Email is sent only when the switch was turned on.
   */
  protected async finish(withNotifications: boolean): Promise<void> {
    if (this.finishing()) return;
    this.finishing.set(true);
    queueTodayTips();
    try {
      if (withNotifications && this.askNotifications()) await this.push.enable();
      if (this.emailToo()) await this.emailSettings.applySignupDefaults();
    } finally {
      void this.router.navigateByUrl('/m/today');
    }
  }

  private async loadChart(kundliId: string): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const cached = this.vedic.cachedAll(kundliId);
      const [chart, story, dashas] = await Promise.all([
        cached ?? this.vedic.all(kundliId),
        this.vedic.story(kundliId).catch(() => null),
        this.vedic.dashas(kundliId).catch(() => null),
      ]);
      this.chart.set(chart);
      this.story.set(story?.story ?? null);
      this.mahadasha.set(dashas?.current?.mahadasha ?? null);
    } catch (e) {
      // The reveal is a bonus, not a gate: a failed fetch here must never
      // block a brand-new signup from reaching the app.
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
}
