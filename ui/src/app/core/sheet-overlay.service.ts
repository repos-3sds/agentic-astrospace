import { Injectable, computed, signal } from '@angular/core';

/**
 * Tracks how many bottom sheets are currently open, app-wide.
 *
 * iOS WebKit traps `position: fixed` descendants inside any ancestor using
 * `-webkit-overflow-scrolling: touch` (mobile-shell's `.content` is one) —
 * they render as if `position: absolute` relative to it instead of escaping
 * to the viewport, no matter how high their z-index is set. A sheet opened
 * from a routed screen nested inside `.content` can therefore never reliably
 * paint over the shell's floating tab bar. Hiding the tab bar while a sheet
 * is open sidesteps the stacking fight entirely instead of fighting a
 * platform quirk with more z-index.
 */
@Injectable({ providedIn: 'root' })
export class SheetOverlayService {
  private readonly count = signal(0);
  readonly open = computed(() => this.count() > 0);

  // Each open sheet registers how to dismiss itself. A plain array rather
  // than relying on `count` for this: dismissTop() needs to call the specific
  // instance's handler, not just know a number is nonzero.
  private readonly dismissers: (() => void)[] = [];

  push(): void {
    this.count.update((n) => n + 1);
  }

  pop(): void {
    this.count.update((n) => Math.max(0, n - 1));
  }

  /** Called by SheetComponent; returns the matching unregister function. */
  registerDismiss(dismiss: () => void): () => void {
    this.dismissers.push(dismiss);
    return () => {
      const i = this.dismissers.indexOf(dismiss);
      if (i !== -1) this.dismissers.splice(i, 1);
    };
  }

  /**
   * Dismiss the most recently opened sheet, if any.
   *
   * The hardware back button's job on Android: a sheet is the thing the
   * reader is looking at, so back should close it rather than falling
   * through to route navigation underneath. Returns whether it found
   * something to close, so the caller knows whether to handle the press
   * itself.
   */
  dismissTop(): boolean {
    const top = this.dismissers[this.dismissers.length - 1];
    if (!top) return false;
    top();
    return true;
  }
}
