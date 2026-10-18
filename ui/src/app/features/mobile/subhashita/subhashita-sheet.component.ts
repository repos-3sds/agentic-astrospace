import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import { Subhashita, SUBHASHITA_TITLE } from '../../../core/subhashita.service';
import { SheetComponent } from '../sheet/sheet.component';
import { SubhashitaVerseComponent } from './subhashita-verse.component';

/** The day's verse, shown once on the first open of each day (see MobileShellComponent). */
@Component({
  selector: 'as-subhashita-sheet',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SheetComponent, SubhashitaVerseComponent],
  template: `
    <as-sheet (dismissed)="dismissed.emit()">
      <header class="head">
        <p class="title">{{ title }}</p>
        <p class="sub">{{ subtitle }}</p>
      </header>
      <as-subhashita-verse [verse]="verse()" />
      <button class="later" type="button" (click)="dismissed.emit()">Continue to the app</button>
      <button class="off" type="button" (click)="turnedOff.emit()">Don't show this when I open the app</button>
    </as-sheet>
  `,
  styles: `
    @use '../mobile-tokens' as *;
    :host { display: contents; }
    .head { display: flex; flex-direction: column; gap: 4px; }
    .title { @include m-h2; color: var(--m-text); margin: 0; }
    .sub { @include m-body-small; color: var(--m-muted); margin: 0; }
    .later { @include m-cta-tertiary; align-self: center; }
    .off { @include m-caption; align-self: center; min-height: 44px; border: 0; background: none; color: var(--m-muted); text-decoration: underline; cursor: pointer; }
  `,
})
export class SubhashitaSheetComponent {
  readonly verse = input.required<Subhashita>();
  readonly dismissed = output<void>();
  /** "Don't show this" (D8): the shell turns the sheet off and closes it. */
  readonly turnedOff = output<void>();
  /** The sheet can open at 9 pm too; "to start the day" read oddly then (D20). */
  protected readonly subtitle = new Date().getHours() < 12 ? 'A verse to start the day with.' : 'Today’s verse.';
  protected readonly title = SUBHASHITA_TITLE;
}
