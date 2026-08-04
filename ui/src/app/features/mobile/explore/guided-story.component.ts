import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { VedicAll } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { buildChartAdapter } from '../chart/mobile-chart-data';

interface StoryCard {
  title: string;
  text: string;
  badge?: 'Blessed' | 'Watch';
  tone: 'good' | 'watch';
}

@Component({
  selector: 'as-guided-story',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './guided-story.component.html',
  styleUrl: './guided-story.component.scss',
})
export class GuidedStoryComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);

  protected readonly chart = signal<VedicAll | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  protected readonly signature = computed(() => {
    const chart = this.chart();
    if (!chart) {
      return {
        headline: 'Your story is being computed.',
        detail: 'Your life map will appear here once your profile loads.',
      };
    }
    const adapter = buildChartAdapter(chart, this.kundlis.active());
    const sun = this.planet('Sun');
    const moon = this.planet('Moon');
    const asc = adapter.angles.find((row) => row.label === 'ASCENDANT')?.sign ?? 'your rising sign';
    return {
      headline: `${this.ascendantArchetype(asc)} shaped by ${sun?.sign ?? 'your Sun'} purpose and ${moon?.sign ?? 'Moon'} intuition.`,
      detail: `Your chart points to ${this.cleanSign(sun?.sign)} self-expression, ${this.cleanSign(moon?.sign)} emotional rhythm, and a ${asc} rising path. This becomes a practical life map, computed from your saved birth details.`,
    };
  });

  protected readonly cards = computed<StoryCard[]>(() => {
    const chart = this.chart();
    if (!chart) return [];
    const jupiter = this.planet('Jupiter');
    const venus = this.planet('Venus');
    const mars = this.planet('Mars');
    const saturn = this.planet('Saturn');
    const moon = this.planet('Moon');
    return [
      {
        title: 'Career & Purpose',
        badge: 'Blessed',
        tone: 'good',
        text: `${this.planetSentence('Jupiter', jupiter)} supports growth through guidance, learning, and purposeful responsibility. ${this.planetSentence('Sun', this.planet('Sun'))} shows where your confidence wants to serve.`,
      },
      {
        title: 'Relationships',
        tone: 'good',
        text: `${this.planetSentence('Venus', venus)} describes how you bond, receive affection, and keep harmony. ${this.planetSentence('Moon', moon)} adds the emotional needs that help love feel safe.`,
      },
      {
        title: 'Health & Energy',
        badge: 'Watch',
        tone: 'watch',
        text: `${this.planetSentence('Mars', mars)} shows your drive and stamina pattern. ${this.planetSentence('Saturn', saturn)} asks you to pace effort, protect rest, and make discipline sustainable.`,
      },
      {
        title: 'Finances',
        tone: 'good',
        text: `${this.planetSentence('Jupiter', jupiter)} and ${this.planetSentence('Venus', venus)} point to steady growth through skill, patience, and well-timed decisions rather than impulse.`,
      },
    ];
  });

  constructor() {
    effect(() => {
      const activeId = this.kundlis.activeId();
      void this.load(activeId);
    });
  }

  protected retry(): void {
    void this.load(this.kundlis.activeId());
  }

  private planet(name: string) {
    return this.chart()?.planets?.[name] ?? null;
  }

  private planetSentence(name: string, row: ReturnType<GuidedStoryComponent['planet']>): string {
    if (!row) return name;
    const house = typeof row.house === 'number' ? ` in your ${this.ordinal(row.house)} house` : '';
    return `${name} in ${row.sign}${house}`;
  }

  private ascendantArchetype(sign: string): string {
    const fire = ['Aries', 'Leo', 'Sagittarius'];
    const earth = ['Taurus', 'Virgo', 'Capricorn'];
    const air = ['Gemini', 'Libra', 'Aquarius'];
    if (fire.includes(sign)) return 'A natural leader';
    if (earth.includes(sign)) return 'A steady builder';
    if (air.includes(sign)) return 'A thoughtful connector';
    return 'An intuitive guide';
  }

  private cleanSign(sign?: string): string {
    return sign ? `${sign}-colored` : 'personal';
  }

  private ordinal(value: number): string {
    const suffix = value % 10 === 1 && value !== 11 ? 'st' : value % 10 === 2 && value !== 12 ? 'nd' : value % 10 === 3 && value !== 13 ? 'rd' : 'th';
    return `${value}${suffix}`;
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
      this.chart.set(this.vedic.cachedAll(activeId) ?? await this.vedic.all(activeId));
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }
}
