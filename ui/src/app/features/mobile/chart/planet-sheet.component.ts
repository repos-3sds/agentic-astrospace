import { ChangeDetectionStrategy, Component, input, output, signal } from '@angular/core';
import { SheetComponent } from '../sheet/sheet.component';

/** What the sheet is told about the tapped placement. */
export interface PlanetDetail {
  /** Two-letter glyph, as written on the chart. */
  abbr: string;
  title: string;
  position: string;
  reading: string;
  house: string;
}

/**
 * Planet detail sheet (Figma node 36:201).
 *
 * Plain reading first, technical detail behind a disclosure. The order matters
 * more here than anywhere else in the chart flow: dignity, nakshatra and
 * lordships are the vocabulary that makes people decide astrology is not for
 * them, and none of it is needed to understand what the placement is saying.
 *
 * Collapsed by default rather than hidden — a reader who wants Shadbala can
 * reach it in one tap, and one who does not is never made to scroll past it.
 */
@Component({
  selector: 'as-planet-sheet',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SheetComponent],
  templateUrl: './planet-sheet.component.html',
  styleUrl: './planet-sheet.component.scss',
})
export class PlanetSheetComponent {
  readonly detail = input.required<PlanetDetail>();

  readonly dismissed = output<void>();
  readonly houseExplainerRequested = output<string>();

  protected readonly technicalOpen = signal(false);

  protected toggleTechnical(): void {
    this.technicalOpen.update((open) => !open);
  }
}
