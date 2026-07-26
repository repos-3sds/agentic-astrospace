import { ChangeDetectionStrategy, Component, output } from '@angular/core';

/**
 * Bottom sheet: scrim plus a rounded panel (Figma nodes 21:23 / 21:24).
 *
 * Shared by every sheet in the app — day-quality detail, why-this-reading,
 * planet detail, provenance, learning — so the scrim opacity, corner radius
 * and handle are defined once and cannot drift between screens.
 *
 * Dismissal is deliberately generous: scrim tap, Escape, and (on the host
 * screen) the primary button all close it. A sheet that can only be dismissed
 * by one affordance is a trap on a phone.
 */
@Component({
  selector: 'as-sheet',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="scrim" (click)="dismissed.emit()" aria-hidden="true"></div>
    <div class="panel" role="dialog" aria-modal="true" (keydown.escape)="dismissed.emit()" tabindex="-1">
      <div class="handle-row"><div class="handle" aria-hidden="true"></div></div>
      <ng-content />
    </div>
  `,
  styleUrl: './sheet.component.scss',
})
export class SheetComponent {
  readonly dismissed = output<void>();
}
