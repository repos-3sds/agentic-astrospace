import { Component, computed, effect, inject, signal } from '@angular/core';
import { Skeleton } from 'primeng/skeleton';

import { KundliStore } from '../../../core/kundli.store';
import {
  GocharaActiveWindow,
  GocharaCoreReadingBlock,
  GocharamPeriod,
  GocharamProfilePayload,
  TransitTimelineEvent,
} from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { SectionCardComponent } from '../../../shared/section-card/section-card.component';

@Component({
  selector: 'app-gocharam-tab',
  imports: [Skeleton, SectionCardComponent],
  templateUrl: './gocharam-tab.component.html',
  styleUrl: './gocharam-tab.component.scss',
})
export class GocharamTabComponent {
  private store = inject(KundliStore);
  private vedic = inject(VedicService);

  protected readonly data = signal<GocharamProfilePayload | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly loading = computed(() => !this.data() && !this.error());
  protected readonly detailMode = signal<'active' | 'next' | 'past'>('active');

  protected readonly currentReading = computed<GocharaCoreReadingBlock | null>(() => {
    const reading = this.data()?.gochara.core_reading;
    if (!reading) return null;
    return {
      title: reading.title,
      tone: reading.tone,
      rationale: reading.rationale,
      reading: reading.reading,
      timing_summary: reading.timing_summary,
    };
  });

  protected readonly readingBlocks = computed<GocharaCoreReadingBlock[]>(() => {
    const core = this.data()?.gochara.core_reading;
    if (!core) return [];
    return [
      {
        title: core.title,
        tone: core.tone,
        rationale: core.rationale,
        reading: core.reading,
        timing_summary: core.timing_summary,
      },
      core.next,
      core.previous,
    ];
  });

  protected readonly activeWindows = computed(() => this.data()?.gochara.timeline.active_windows ?? []);
  protected readonly detailEvents = computed(() => {
    const timeline = this.data()?.gochara.timeline;
    if (!timeline) return [];
    if (this.detailMode() === 'next') return timeline.next_365_days;
    if (this.detailMode() === 'past') return timeline.previous_365_days;
    return [];
  });

  constructor() {
    effect(() => {
      const id = this.store.activeId();
      this.data.set(null);
      this.error.set(null);
      if (!id) return;
      this.vedic
        .gocharam(id)
        .then((payload) => this.data.set(payload))
        .catch((e) => this.error.set((e as Error).message));
    });
  }

  protected toneClass(tone?: string): string {
    if (tone === 'supportive') return 'supportive';
    if (tone === 'challenging' || tone === 'hard' || tone === 'mixed') return 'challenging';
    return 'neutral';
  }

  protected formatDate(value?: string | null): string {
    if (!value) return 'Open';
    return new Intl.DateTimeFormat('en', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(new Date(`${value}T12:00:00`));
  }

  protected formatRange(window: GocharaActiveWindow): string {
    return `${this.formatDate(window.start_date)} -> ${this.formatDate(window.end_date)}`;
  }

  protected eventTrack(event: TransitTimelineEvent): string {
    return `${event.date}-${event.rule || event.title}-${event.transition || event.type}`;
  }

  protected periodTrack(period: GocharamPeriod): string {
    return `${period.status}-${period.rule_id}-${period.start_date}-${period.end_date}`;
  }
}
