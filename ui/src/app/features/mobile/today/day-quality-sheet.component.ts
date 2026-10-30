import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { SheetComponent } from '../sheet/sheet.component';
import type { DayBand, DayPart } from './today.component';

/** One computed contributor to the day score. */
export interface DaySignal {
  name: string;
  verdict: string;
  tone: 'good' | 'warn' | 'bad';
  explanation: string;
}

/**
 * Day-quality detail (Figma node 21:22) — Epic C2's "tapped, it expands to the
 * plain reasons".
 *
 * The point of this sheet is that the score is *derived*, not pronounced: each
 * contributing signal is named, graded and explained in plain language. That is
 * the design principle about data honesty, so the signals are listed
 * individually rather than summarised into one sentence.
 *
 * It also says what each band means (testers could not tell what a "26"
 * meant, 2026-10-28). Hawk wanted these lines here only, not on the Today
 * screen itself.
 */
@Component({
  selector: 'as-day-quality-sheet',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SheetComponent],
  templateUrl: './day-quality-sheet.component.html',
  styleUrl: './day-quality-sheet.component.scss',
})
export class DayQualitySheetComponent {
  readonly score = input.required<number>();
  readonly band = input.required<DayBand>();
  readonly signals = input.required<DaySignal[]>();
  readonly summary = input.required<string>();
  readonly reason = input.required<string>();
  /** The day's parts when the star or the Moon's sign changes; empty otherwise. */
  readonly parts = input<DayPart[]>([]);
  readonly dismissed = output<void>();

  protected readonly bands: { band: DayBand; range: string; label: string; rubric: string }[] = [
    { band: 'good', range: '70–100', label: 'Good', rubric: 'Things line up for you. A good day to begin something.' },
    { band: 'steady', range: '50–69', label: 'Steady', rubric: 'A normal, workable day. Keep your routine going.' },
    { band: 'mixed', range: '30–49', label: 'Mixed', rubric: 'Some help, some pull. Go at your pace, skip big risks.' },
    { band: 'tough', range: '0–29', label: 'Go gently', rubric: 'A quiet day. Keep it simple and save big moves for later.' },
  ];
}
