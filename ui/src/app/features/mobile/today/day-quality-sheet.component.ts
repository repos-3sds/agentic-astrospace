import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { SheetComponent } from '../sheet/sheet.component';

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
  readonly signals = input.required<DaySignal[]>();
  readonly summary = input.required<string>();
  readonly reason = input.required<string>();
  readonly dismissed = output<void>();
  // MOCKUP ONLY
  protected readonly bands = [
    { band: 'good', from: 70, to: 100, label: 'Good', rubric: 'Things line up for you. A good day to begin something.' },
    { band: 'steady', from: 50, to: 69, label: 'Steady', rubric: 'A normal, workable day. Keep your routine going.' },
    { band: 'mixed', from: 30, to: 49, label: 'Mixed', rubric: 'Some help, some pull. Go at your pace, skip big risks.' },
    { band: 'tough', from: 0, to: 29, label: 'Go gently', rubric: 'A quiet day. Keep it simple and save big moves for later.' },
  ];
}
