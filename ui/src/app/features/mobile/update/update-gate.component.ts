import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';

import { AppUpdateService } from '../../../core/app-update.service';

/**
 * The whole screen, over everything, while this build is too old to open
 * (AppUpdateService.blocked): only when Hawk has marked a newer build
 * required, or set a grace period that has passed. One way out, the update;
 * coming back from the store checks again, so an updated app opens as usual.
 */
@Component({
  selector: 'as-update-gate',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'as-mobile' },
  template: `
    <section class="gate" role="alertdialog" aria-modal="true" aria-labelledby="update-gate-title" aria-describedby="update-gate-body">
      <img class="orb" src="mobile/orb.svg" alt="" aria-hidden="true" />
      <h1 class="title" id="update-gate-title">Please update Siddha</h1>
      <p class="body" id="update-gate-body">
        This version of Siddha has stopped working. The new one takes a minute to install from
        {{ updates.store() }}, and your profiles, notes and settings stay as they are.
      </p>
      <button class="primary" type="button" (click)="update()">{{ opening() ? 'Opening…' : 'Update now' }}</button>
      <button class="again" type="button" (click)="updates.check(true)">I have updated</button>
    </section>
  `,
  styles: `
    @use '../mobile-tokens' as *;
    :host {
      position: fixed;
      inset: 0;
      z-index: 10000;
      display: flex;
      background: var(--m-app-ground, var(--m-bg));
      background-color: var(--m-bg);
    }
    .gate {
      margin: auto;
      box-sizing: border-box;
      width: 100%;
      max-width: 420px;
      padding: calc(24px + var(--as-safe-top, 0px)) 24px calc(24px + var(--as-safe-bottom, 0px));
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 14px;
      text-align: center;
    }
    .orb { width: 88px; height: 88px; margin-bottom: 8px; }
    .title { @include m-h2; color: var(--m-text); margin: 0; }
    .body { @include m-body; color: var(--m-muted); margin: 0; }
    .primary { @include m-cta-primary; width: 100%; margin-top: 12px; }
    .again { @include m-cta-tertiary; min-height: 44px; }
  `,
})
export class UpdateGateComponent {
  protected readonly updates = inject(AppUpdateService);
  protected readonly opening = signal(false);

  async update(): Promise<void> {
    this.opening.set(true);
    try {
      await this.updates.update();
    } finally {
      setTimeout(() => this.opening.set(false), 1500);
    }
  }
}
