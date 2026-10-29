import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { AppUpdateService } from '../../../core/app-update.service';
import { SheetComponent } from '../sheet/sheet.component';

/**
 * "A new version of Siddha is ready": shown by the shell while this build is
 * behind the one readers can install (AppUpdateService.offer). Says where to
 * update and that nothing is lost; never what is new, so a build can be
 * announced in its own time.
 */
@Component({
  selector: 'as-update-sheet',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SheetComponent],
  template: `
    <as-sheet (dismissed)="updates.later()">
      <header class="head">
        <img class="orb" src="mobile/orb.svg" alt="" aria-hidden="true" />
        <h2 class="title">A new version of Siddha is ready</h2>
        <p class="sub">
          Update from {{ updates.store() }} when you have a minute. Your profiles, notes and settings stay as they are.
        </p>
      </header>
      <button class="primary" type="button" (click)="updates.update()">Update now</button>
      <button class="later" type="button" (click)="updates.later()">Later</button>
    </as-sheet>
  `,
  styles: `
    @use '../mobile-tokens' as *;
    :host { display: contents; }
    .head { display: flex; flex-direction: column; align-items: center; gap: 8px; text-align: center; padding-top: 4px; }
    .orb { width: 56px; height: 56px; }
    .title { @include m-h2; color: var(--m-text); margin: 0; }
    .sub { @include m-body; color: var(--m-muted); margin: 0; max-width: 34ch; }
    .primary { @include m-cta-primary; width: 100%; margin-top: 8px; }
    .later { @include m-cta-tertiary; align-self: center; min-height: 44px; }
  `,
})
export class UpdateSheetComponent {
  protected readonly updates = inject(AppUpdateService);
}
