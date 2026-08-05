import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ManglikCancellationSheetComponent } from './manglik-cancellation-sheet.component';
import { YogaLearningDetail, YogaLearningSheetComponent } from './yoga-learning-sheet.component';
import { KundliStore } from '../../../core/kundli.store';
import { DoshasPayload, YogaResult, YogasDoshasPayload } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';

type Kind = 'yoga' | 'dosha';
type Filter = 'all' | Kind;

interface Combination {
  id: string;
  kind: Kind;
  title: string;
  tag: string;
  tone: 'good' | 'gold' | 'bad' | 'neutral';
  summary: string;
  cancelled?: string;
  source?: string;
  chartFact?: string;
}

/** Yogas & Doshas overview and filtering (Figma node 41:87). */
@Component({
  selector: 'as-yogas-doshas',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, YogaLearningSheetComponent, ManglikCancellationSheetComponent],
  templateUrl: './yogas-doshas.component.html',
  styleUrl: './yogas-doshas.component.scss',
})
export class YogasDoshasComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  readonly filter = signal<Filter>('all');
  readonly learningOpen = signal(false);
  readonly selectedLearning = signal<YogaLearningDetail | null>(null);
  readonly cancellationOpen = signal(false);
  protected readonly data = signal<YogasDoshasPayload | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  readonly items = computed<Combination[]>(() => [
    ...((this.data()?.yogas.active ?? []).map((yoga) => this.yogaItem(yoga))),
    ...this.doshaItems(this.data()?.doshas ?? null),
  ]);
  readonly visibleItems = computed(() =>
    this.filter() === 'all' ? this.items() : this.items().filter((item) => item.kind === this.filter()),
  );

  constructor() {
    effect(() => {
      const activeId = this.kundlis.activeId();
      void this.load(activeId);
    });
  }

  protected learn(item: Combination): void {
    if (item.id === 'manglik') this.cancellationOpen.set(true);
    else {
      this.selectedLearning.set({
        title: item.title,
        summary: item.summary,
        source: item.source ?? 'Source review is not available for this combination yet.',
        chartFact: item.chartFact ?? item.cancelled ?? 'This combination was returned for your selected chart by the live calculation service.',
      });
      this.learningOpen.set(true);
    }
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
      if (!activeId) {
        this.data.set(null);
        return;
      }
      this.data.set(await this.vedic.yogasDoshas(activeId));
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  private yogaItem(yoga: YogaResult): Combination {
    return {
      id: yoga.rule_id ?? yoga.name,
      kind: 'yoga',
      title: yoga.name,
      tag: yoga.strength || this.statusLabel(yoga),
      tone: yoga.category.toLowerCase().includes('caution') ? 'bad' : yoga.verified ? 'good' : 'gold',
      summary: yoga.rule || yoga.triggers.join(' · ') || 'Backend returned this yoga without additional detail.',
      cancelled: yoga.notes?.[0],
      source: yoga.source_refs?.map((row) => `${row.source}: ${row.detail}`).join(' · ')
        ?? this.statusLabel(yoga),
      chartFact: yoga.triggers.join(' · ') || yoga.notes?.[0],
    };
  }

  private doshaItems(doshas: DoshasPayload | null): Combination[] {
    if (!doshas) return [];
    const items: Combination[] = [];
    if (doshas.manglik) {
      const exception = doshas.manglik.exceptions?.find((row) => row.applies);
      items.push({
        id: 'manglik',
        kind: 'dosha',
        title: doshas.manglik.name || 'Manglik Dosha',
        tag: doshas.manglik.active ? `FLAG · ${doshas.manglik.net_severity ?? doshas.manglik.severity}` : 'NOT PRESENT',
        tone: doshas.manglik.active ? 'bad' : 'neutral',
        summary: doshas.manglik.rule,
        cancelled: exception ? `Exception applies: ${exception.detail}` : doshas.manglik.notes?.[0],
        source: doshas.manglik.source_refs?.map((row) => `${row.source}: ${row.detail}`).join(' · ')
          ?? doshas.manglik.source_status
          ?? 'Classical source not returned by the backend.',
      });
    }
    for (const row of [doshas.gandanta, doshas.grahan].filter(Boolean)) {
      items.push({
        id: row!.rule_id ?? row!.name,
        kind: 'dosha',
        title: row!.name,
        tag: row!.active ? `FLAG · ${row!.severity}` : 'NOT PRESENT',
        tone: row!.active ? 'bad' : 'neutral',
        summary: row!.rule,
        cancelled: row!.notes?.[0],
        source: row!.source_refs?.map((source) => `${source.source}: ${source.detail}`).join(' · ')
          ?? row!.source_status
          ?? 'Classical source not returned by the backend.',
      });
    }
    return items;
  }

  private statusLabel(row: YogaResult): string {
    if (row.source_status === 'verified_common') return 'VERIFIED';
    if (row.source_status === 'convention_dependent') return 'CONVENTION';
    if (row.source_status === 'needs_review') return 'REVIEW';
    return row.verified ? 'VERIFIED' : 'REVIEW';
  }
}
