import { ChangeDetectionStrategy, Component, output } from '@angular/core';
import { SheetComponent } from '../sheet/sheet.component';

@Component({
  selector: 'as-festival-sheet',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SheetComponent],
  template: `
    <as-sheet (dismissed)="dismissed.emit()">
      <header class="mcal-festival-head">
        <span class="mcal-date-tile"><b>29</b><small>JUL</small></span>
        <span><h2>Naga Panchami</h2><p>Wednesday · 4 days away</p></span>
      </header>
      <p class="mcal-festival-copy">A day of reverence for serpent deities — offerings and prayers for protection and family wellbeing, especially observed by those with Rahu/Ketu concerns in their chart.</p>
      <p class="mcal-eyebrow">HOW TO PREPARE</p>
      <ul class="mcal-prepare">
        <li>Visit a temple at sunrise, or offer milk at an anthill/snake idol if available.</li>
        <li>Fast until the offering is complete, if that is your practice.</li>
        <li>A simple prayer at home is equally valid — this is about intention, not extravagance.</li>
      </ul>
      <p class="mcal-window"><img src="mobile/clock.svg" alt="" aria-hidden="true" />Best window: 5:45–7:30 AM, before Rahu Kalam</p>
      <button class="mcal-remind" type="button" (click)="reminded = true">{{ reminded ? 'Reminder set' : 'Remind me that morning' }}</button>
    </as-sheet>
  `,
  styleUrl: './festival-sheet.component.scss',
})
export class FestivalSheetComponent {
  readonly dismissed = output<void>();
  reminded = false;
}
