import { ChangeDetectionStrategy, Component, output } from '@angular/core';
import { SheetComponent } from '../sheet/sheet.component';

/** Shared Manglik cancellation explanation (Figma node 62:140). */
@Component({
  selector: 'as-manglik-cancellation-sheet',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SheetComponent],
  template: `
    <as-sheet (dismissed)="dismissed.emit()">
      <header class="head">
        <p class="flag">MARRIAGE · FLAG, CANCELLED</p>
        <h2>Why your Manglik is cancelled</h2>
      </header>
      <p class="body">Mars sits in your 7th house, which is traditionally flagged as Manglik dosha. But classical rules also recognize exceptions — and your chart meets one of them.</p>
      <section class="exception">
        <h3><img src="mobile/cancellation-check.svg" alt="" aria-hidden="true" />Exception met: Mars in own sign</h3>
        <p>Mars is in Scorpio, one of its own signs. Classical texts (BPHS) state that Mars in its own sign, exaltation, or a kendra from the Moon cancels the dosha’s effect.</p>
      </section>
      <p class="eyebrow">WHAT THIS MEANS FOR YOU</p>
      <p class="body">Most practitioners would not weigh this placement heavily in matchmaking. It’s worth mentioning to your family astrologer, but it isn’t something to be anxious about.</p>
      <button class="got-it" type="button" (click)="dismissed.emit()">Got it</button>
    </as-sheet>
  `,
  styleUrl: './manglik-cancellation-sheet.component.scss',
})
export class ManglikCancellationSheetComponent {
  readonly dismissed = output<void>();
}
