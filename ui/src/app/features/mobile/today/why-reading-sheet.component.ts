import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { SheetComponent } from '../sheet/sheet.component';

/** One row of the computed basis behind a reading. */
export interface EvidenceRow {
  label: string;
  value: string;
}

/**
 * "Why this reading?" (Figma node 22:23) — Epic J's evidence surface.
 *
 * The design's own subtitle states the rule this screen exists to enforce:
 * plain first, the calculation underneath. Plain-words bullets come before
 * THE CALCULATION, and the convention chips (ayanamsa, house system, place,
 * confidence) are always present — a reading whose conventions are hidden is
 * not reproducible, and the same numbers under a different ayanamsa are a
 * different answer.
 */
@Component({
  selector: 'as-why-reading-sheet',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SheetComponent],
  templateUrl: './why-reading-sheet.component.html',
  styleUrl: './why-reading-sheet.component.scss',
})
export class WhyReadingSheetComponent {
  readonly mode = input('Balanced view — plain first, the calculation underneath.');
  readonly plainWords = input.required<string[]>();
  readonly calculation = input.required<EvidenceRow[]>();
  readonly conventions = input.required<string[]>();
  readonly dismissed = output<void>();
  readonly learnTerms = output<void>();
}
