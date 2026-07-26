import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { SheetComponent } from '../sheet/sheet.component';

/** One line of the calculation trail. */
export interface ProvenanceRow {
  label: string;
  value: string;
}

/**
 * Provenance sheet (Figma node 36:247) — "How this was computed".
 *
 * The gold note is the point of the screen, not a caveat attached to it:
 * ayanamsha and house system are genuinely disputed in the tradition, and two
 * competent astrologers using different ones will disagree about the same
 * birth. Naming the choice is what makes a reading reproducible; hiding it
 * would imply a precision the tradition does not have.
 *
 * Every row here is a convention or an input, never a conclusion. Nothing in
 * this sheet should ever need softening, because nothing in it is a claim.
 */
@Component({
  selector: 'as-provenance-sheet',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SheetComponent],
  templateUrl: './provenance-sheet.component.html',
  styleUrl: './provenance-sheet.component.scss',
})
export class ProvenanceSheetComponent {
  readonly rows = input<ProvenanceRow[]>([
    { label: 'Ephemeris', value: 'Swiss Ephemeris (Moshier)' },
    { label: 'Ayanamsha', value: 'Lahiri' },
    { label: 'Node type', value: 'Mean' },
    { label: 'House system', value: 'Whole-sign' },
    { label: 'Calculation place', value: 'Vijayawada, India' },
    { label: 'Birth time confidence', value: 'High' },
  ]);

  readonly dismissed = output<void>();
  readonly settingsRequested = output<void>();
}
