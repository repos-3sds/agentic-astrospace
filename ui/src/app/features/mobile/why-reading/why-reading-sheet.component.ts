import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { SheetComponent } from '../sheet/sheet.component';

/** One row of the computed basis behind a reading. */
export interface EvidenceRow {
  label: string;
  value: string;
}

/** One classical-text citation behind a reading — see context.references. */
export interface SourceReference {
  statement: string;
  source_location: string;
}

/** One Do/Avoid card headline, expanded to its full reasoning. */
export interface DoAvoidExplainer {
  kind: 'do' | 'avoid';
  headline: string;
  detail: string;
}

/**
 * "Why this reading?" (Figma node 22:23) — Epic J's evidence surface.
 *
 * Shared, not Today's: the answer view (26:54) opens the same sheet from its
 * own "Why this?" row, and every reading in the app owes the same account of
 * itself. It lives outside both features so neither owns it.
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
  /** Real classical-text citations, when the caller has them. Optional — the
   * Ask answer sheet doesn't route through the Context Engine's KB yet. */
  readonly references = input<SourceReference[]>([]);
  /** Full reasoning behind each Do/Avoid card headline. Optional — only
   * Today's reading has Do/Avoid rows to expand. */
  readonly doAvoidExplained = input<DoAvoidExplainer[]>([]);
  readonly conventions = input.required<string[]>();
  readonly dismissed = output<void>();
  readonly learnTerms = output<void>();
}
