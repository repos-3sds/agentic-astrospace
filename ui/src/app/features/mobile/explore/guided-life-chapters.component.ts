import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { DashaPayload, DashaPeriod } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';

interface TimelineItem {
  title: string;
  detail: string;
  active?: boolean;
  future?: boolean;
}

@Component({
  selector: 'as-guided-life-chapters',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './guided-life-chapters.component.html',
  styleUrl: './guided-life-chapters.component.scss',
})
export class GuidedLifeChaptersComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);

  protected readonly dashas = signal<DashaPayload | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  protected readonly current = computed(() => {
    const dasha = this.dashas()?.current.mahadasha ?? this.dashas()?.mahadashas.find((row) => row.active) ?? null;
    const lord = dasha?.lord ?? 'Saturn';
    return {
      lord,
      title: `${lord}'s ${this.chapterMood(lord)} Phase`,
      dates: dasha ? `${this.dateLabel(dasha.start)} · ${this.chapterLine(lord)}` : 'Since January 2026 · Steady effort favoured, avoid shortcuts.',
      progress: dasha ? this.progress(dasha) : 34,
      start: dasha ? new Date(dasha.start).getFullYear() : 2025,
      end: dasha ? new Date(dasha.end).getFullYear() : 2028,
    };
  });

  protected readonly timeline = computed<TimelineItem[]>(() => {
    const periods = this.dashas()?.mahadashas;
    if (!periods?.length) return FALLBACK_TIMELINE;
    const activeIndex = Math.max(0, periods.findIndex((period) => period.active));
    return periods.slice(Math.max(0, activeIndex - 4), activeIndex + 2).map((period, index, rows) => ({
      title: `${period.lord} Chapter`,
      detail: `${this.dateLabel(period.start)}-${this.dateLabel(period.end)} · ${this.chapterLine(period.lord)}`,
      active: period.active,
      future: !period.active && index === rows.length - 1,
    }));
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

  private async load(expectedActiveId: string | null): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
      const activeId = this.kundlis.activeId();
      if (expectedActiveId && activeId !== expectedActiveId) return;
      this.dashas.set(activeId ? await this.vedic.dashas(activeId) : null);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  private progress(period: DashaPeriod): number {
    const start = new Date(period.start).getTime();
    const end = new Date(period.end).getTime();
    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return 34;
    return Math.max(8, Math.min(92, ((Date.now() - start) / (end - start)) * 100));
  }

  private dateLabel(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value || '—';
    return date.getFullYear().toString();
  }

  private chapterMood(lord: string): string {
    return ({
      Saturn: 'Steady',
      Venus: 'Creative',
      Sun: 'Visible',
      Moon: 'Feeling',
      Mars: 'Active',
      Mercury: 'Learning',
      Jupiter: 'Expansive',
      Rahu: 'Changing',
      Ketu: 'Reflective',
    } as Record<string, string>)[lord] ?? 'Current';
  }

  private chapterLine(lord: string): string {
    return ({
      Saturn: 'Discipline, patience & foundations',
      Venus: 'Beauty, devotion & relationships',
      Sun: 'Identity, courage & right visibility',
      Moon: 'Emotional rhythm & inner listening',
      Mars: 'Drive, action & disciplined effort',
      Mercury: 'Communication, learning & adaptability',
      Jupiter: 'Growth, teachers & purpose',
      Rahu: 'Change, appetite & new territory',
      Ketu: 'Reflection, release & inner clarity',
    } as Record<string, string>)[lord] ?? 'A meaningful life chapter';
  }
}

const FALLBACK_TIMELINE: TimelineItem[] = [
  { title: 'Venus Chapter', detail: '2013-2019 · Beauty, devotion & relationships' },
  { title: 'Sun Chapter', detail: '2019-2020 · Identity, courage & right visibility' },
  { title: 'Moon Chapter', detail: '2020-2023 · Emotional rhythm & inner listening' },
  { title: 'Mars Chapter', detail: '2023-2025 · Drive, action & disciplined effort' },
  { title: 'Saturn Chapter', detail: '2025-2028 · Discipline, patience & foundations', active: true },
  { title: 'Mercury Chapter', detail: '2028-2031 · Communication & rapid learning', future: true },
];
