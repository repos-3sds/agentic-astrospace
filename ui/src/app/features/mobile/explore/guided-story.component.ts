import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { VedicAll } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { buildChartAdapter } from '../chart/mobile-chart-data';

interface StoryCard {
  title: string;
  text: string;
  practice: string;
  source: string;
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
      detail: `Your story is read from your ascendant, Sun, Moon and the planets that shape each life area. It is guidance first, with the chart source kept visible.`,
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
        text: this.domainReading('career', jupiter, this.planet('Sun')),
        practice: 'Choose work that lets you guide, teach, improve systems, or carry responsibility without losing emotional steadiness.',
        source: this.sourceLine('Jupiter', jupiter, 'Sun', this.planet('Sun')),
      },
      {
        title: 'Relationships',
        tone: 'good',
        text: this.domainReading('relationships', venus, moon),
        practice: 'Let care be clear and consistent. Speak needs before they become tests, and choose bonds that respect your rhythm.',
        source: this.sourceLine('Venus', venus, 'Moon', moon),
      },
      {
        title: 'Health & Energy',
        badge: 'Watch',
        tone: 'watch',
        text: this.domainReading('health', mars, saturn),
        practice: 'Use discipline gently: regular sleep, clean food, movement, and pauses before burnout. Avoid proving strength through overwork.',
        source: this.sourceLine('Mars', mars, 'Saturn', saturn),
      },
      {
        title: 'Finances',
        tone: 'good',
        text: this.domainReading('finances', jupiter, venus),
        practice: 'Build slowly. Favor skill, savings, and thoughtful timing over pressure, display, or impulse spending.',
        source: this.sourceLine('Jupiter', jupiter, 'Venus', venus),
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

  private domainReading(
    domain: 'career' | 'relationships' | 'health' | 'finances',
    primary: ReturnType<GuidedStoryComponent['planet']>,
    secondary: ReturnType<GuidedStoryComponent['planet']>,
  ): string {
    const primaryHouse = typeof primary?.house === 'number' ? primary.house : null;
    const secondaryHouse = typeof secondary?.house === 'number' ? secondary.house : null;
    const angular = [1, 4, 7, 10];
    const growth = [1, 5, 9, 10, 11];
    const inner = [4, 8, 12];
    const relationship = [2, 4, 7, 11];
    const discipline = [6, 8, 12];

    if (domain === 'career') {
      if (primaryHouse && angular.includes(primaryHouse)) {
        return 'Purpose grows when you stand visibly for something useful. You are not meant to drift; you do best when people can rely on your judgement.';
      }
      if (primaryHouse && growth.includes(primaryHouse)) {
        return 'Career expands through learning, counsel, networks and long-range choices. The chart favors earned credibility over sudden reinvention.';
      }
      return 'Your work path strengthens when skill and service come before recognition. Progress may feel gradual, but it becomes durable.';
    }

    if (domain === 'relationships') {
      if (primaryHouse && relationship.includes(primaryHouse)) {
        return 'Relationships become a major mirror for your life. Love works best when affection is practical, spoken, and steady rather than guessed.';
      }
      if (secondaryHouse && inner.includes(secondaryHouse)) {
        return 'You bond deeply, but emotional safety matters. The right relationships give room for privacy, repair, and honest tenderness.';
      }
      return 'Your chart asks for loyalty with clarity. Warmth is important, but so are boundaries and shared responsibility.';
    }

    if (domain === 'health') {
      if ((primaryHouse && discipline.includes(primaryHouse)) || (secondaryHouse && discipline.includes(secondaryHouse))) {
        return 'Energy is strongest when life is rhythmic. Stress accumulates when you carry too much silently, so prevention matters more than recovery.';
      }
      return 'Vitality improves through steady movement and emotional balance. Your body responds well to simple routines repeated without drama.';
    }

    if (primaryHouse && growth.includes(primaryHouse)) {
      return 'Money improves through knowledge, reputation and timing. The chart favors patient accumulation and wise advisors over risky shortcuts.';
    }
    return 'Finances ask for moderation. You grow by protecting value, avoiding pressure decisions, and making wealth serve a calmer life.';
  }

  private sourceLine(
    firstName: string,
    first: ReturnType<GuidedStoryComponent['planet']>,
    secondName: string,
    second: ReturnType<GuidedStoryComponent['planet']>,
  ): string {
    return `Based on ${this.planetSentence(firstName, first)} and ${this.planetSentence(secondName, second)}.`;
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
