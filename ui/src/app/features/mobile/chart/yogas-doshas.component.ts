import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ManglikCancellationSheetComponent } from './manglik-cancellation-sheet.component';
import { YogaLearningSheetComponent } from './yoga-learning-sheet.component';

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
  readonly filter = signal<Filter>('all');
  readonly learningOpen = signal(false);
  readonly cancellationOpen = signal(false);
  readonly items: Combination[] = [
    {
      id: 'gajakesari', kind: 'yoga', title: 'Gajakesari Yoga', tag: 'STRONG',
      tone: 'good',
      summary: 'Moon and Jupiter in mutual kendra (1-4-7-10) — a classical marker of wisdom and steady reputation.',
    },
    {
      id: 'raja', kind: 'yoga', title: 'Raja Yoga', tag: 'PARIVARTANA',
      tone: 'gold',
      summary: 'Your 9th and 10th lords exchange signs — a supportive placement for career recognition over time.',
    },
    {
      id: 'manglik', kind: 'dosha', title: 'Manglik Dosha', tag: 'FLAG · CANCELLED',
      tone: 'bad',
      summary: 'Mars in the 7th house — a commonly-flagged marriage placement.',
      cancelled: 'Cancelled: Mars is in its own sign, a classical exception.',
    },
    {
      id: 'kalasarpa', kind: 'dosha', title: 'Kalasarpa Dosha', tag: 'NOT PRESENT',
      tone: 'neutral',
      summary: 'All planets are not hemmed between Rahu and Ketu — this dosha does not apply to your chart.',
    },
  ];
  readonly visibleItems = computed(() =>
    this.filter() === 'all' ? this.items : this.items.filter((item) => item.kind === this.filter()),
  );

  protected learn(item: Combination): void {
    if (item.id === 'manglik') this.cancellationOpen.set(true);
    else if (item.id === 'gajakesari') this.learningOpen.set(true);
  }
}
