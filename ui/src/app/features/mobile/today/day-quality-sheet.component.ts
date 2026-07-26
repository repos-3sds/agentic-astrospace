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
  readonly dismissed = output<void>();
}
