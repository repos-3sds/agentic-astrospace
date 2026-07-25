import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';
import { DayGaugeComponent } from '../day-gauge/day-gauge.component';

/** Verdict bands. Named, not numeric, so tone rules can key off them. */
export type DayBand = 'steady' | 'mixed' | 'tough';

export interface TodayView {
  greetingName: string;
  initial: string;
  dateLabel: string;
  place: string;
  score: number;
  band: DayBand;
  scoreLabel: string;
  verdict: string;
  detail: string;
  doItem: string;
  avoidItem: string;
  nextWindowLabel: string;
  nextWindowValue: string;
  nextWindowIn: string;
}

/**
 * Today — the app's home (Figma node 13:2), per Epic C.
 *
 * C1 requires one viewport to carry a plain verdict, one thing to do, one to
 * avoid, and a day-quality indicator; everything deeper is a swipe away. The
 * order here follows the design exactly rather than being re-derived.
 *
 * The copy below is the design's placeholder content. Wiring to
 * /api/v1/panchanga/{id}/today is the next step; the view model is already
 * shaped for it so the template does not change when real data lands.
 */
@Component({
  selector: 'as-today',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DayGaugeComponent],
  templateUrl: './today.component.html',
  styleUrl: './today.component.scss',
})
export class TodayComponent {
  readonly view = signal<TodayView>({
    greetingName: 'Lakshmi',
    initial: 'L',
    dateLabel: 'Friday, 25 July',
    place: 'Vijayawada',
    score: 72,
    band: 'steady',
    scoreLabel: 'Steady',
    verdict: 'A steady, workable day',
    detail:
      'Good momentum for work and errands — keep big money calls for the afternoon.',
    doItem: 'Start the work you’ve been delaying.',
    avoidItem: 'Signing final papers before noon.',
    nextWindowLabel: 'NEXT WINDOW TO AVOID',
    nextWindowValue: 'Rahu Kalam · 4:30–6:00 PM',
    nextWindowIn: 'in 2h',
  });

  protected readonly greeting = computed(() => `Namaste, ${this.view().greetingName}`);
}
