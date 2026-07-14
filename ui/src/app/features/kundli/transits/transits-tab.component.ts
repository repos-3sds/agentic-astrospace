import { Component, computed, effect, inject, signal } from '@angular/core';
import { Skeleton } from 'primeng/skeleton';

import { KundliStore } from '../../../core/kundli.store';
import {
  AshtakavargaTransitPlanet,
  TransitAnalysisPayload,
  TransitAspect,
  TransitRule,
  TransitTimelineEvent,
} from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { SectionCardComponent } from '../../../shared/section-card/section-card.component';

@Component({
  selector: 'app-transits-tab',
  imports: [Skeleton, SectionCardComponent],
  templateUrl: './transits-tab.component.html',
  styleUrl: './transits-tab.component.scss',
})
export class TransitsTabComponent {
  private store = inject(KundliStore);
  private vedic = inject(VedicService);

  protected readonly data = signal<TransitAnalysisPayload | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly loading = computed(() => !this.data() && !this.error());
  protected readonly timelineMode = signal<'seven' | 'thirty'>('seven');
  protected readonly gocharaTimelineMode = signal<'active' | 'next' | 'past'>('active');

  protected readonly gocharaPlanets = computed(() => {
    const planets = this.data()?.gochara.planets ?? {};
    const order = ['Saturn', 'Jupiter', 'Rahu', 'Ketu', 'Mars', 'Sun', 'Moon', 'Venus', 'Mercury'];
    return order.flatMap((planet) => (planets[planet] ? [planets[planet]] : []));
  });

  protected readonly strongest = computed(() => this.data()?.strongest_aspect ?? null);

  protected readonly avTransit = computed(() => this.data()?.ashtakavarga_transit ?? null);
  protected readonly avPlanets = computed<AshtakavargaTransitPlanet[]>(() => {
    const planets = this.avTransit()?.planets ?? {};
    const order = ['Saturn', 'Jupiter', 'Mars', 'Sun', 'Moon', 'Venus', 'Mercury'];
    return order.flatMap((planet) => (planets[planet] ? [planets[planet]] : []));
  });
  protected readonly activeRules = computed(() => this.data()?.gochara.active_rules ?? []);
  protected readonly majorAspects = computed(() => (this.data()?.active_aspects ?? []).slice(0, 12));
  protected readonly gocharaTimelineEvents = computed(() => {
    const timeline = this.data()?.gochara.timeline;
    if (!timeline) return [];
    if (this.gocharaTimelineMode() === 'past') return timeline.previous_365_days;
    if (this.gocharaTimelineMode() === 'next') return timeline.next_365_days;
    return [];
  });
  protected readonly timelineEvents = computed(() => {
    const timeline = this.data()?.timeline;
    if (!timeline) return [];
    return this.timelineMode() === 'seven' ? timeline.next_7_days : timeline.next_30_days;
  });

  constructor() {
    effect(() => {
      const id = this.store.activeId();
      this.data.set(null);
      this.error.set(null);
      if (!id) return;
      this.vedic
        .transits(id)
        .then((payload) => this.data.set(payload))
        .catch((e) => this.error.set((e as Error).message));
    });
  }

  protected aspectTitle(aspect: TransitAspect | null): string {
    if (!aspect) return 'No major active aspect';
    return `${aspect.transit_planet} ${aspect.aspect.toLowerCase()} natal ${aspect.natal_planet}`;
  }

  protected toneClass(tone?: string): string {
    if (tone === 'supportive') return 'supportive';
    if (tone === 'challenging' || tone === 'hard' || tone === 'mixed') return 'challenging';
    return 'neutral';
  }

  protected formatDate(value: string): string {
    return new Intl.DateTimeFormat('en', {
      month: 'short',
      day: 'numeric',
    }).format(new Date(`${value}T12:00:00`));
  }

  protected formatDateTime(value: string): string {
    return new Intl.DateTimeFormat('en', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value));
  }

  protected formatRange(start?: string | null, end?: string | null): string {
    const startLabel = start ? this.formatDate(start) : 'Before scan';
    const endLabel = end ? this.formatDate(end) : 'Beyond scan';
    return `${startLabel} → ${endLabel}`;
  }

  protected eventTrack(event: TransitTimelineEvent): string {
    return `${event.date}-${event.type}-${event.planet}-${event.title}`;
  }

  protected bindusClass(bindus: number): string {
    if (bindus >= 5) return 'good';
    if (bindus === 4) return 'neutral';
    return 'warn';
  }

  protected ruleSeverityLabel(rule: TransitRule): string {
    if (!rule.active) return 'inactive';
    const effective = rule.effective_severity;
    if (effective && effective !== rule.severity) {
      return `${rule.severity} → ${effective} (AV)`;
    }
    return effective ?? rule.severity;
  }
}
