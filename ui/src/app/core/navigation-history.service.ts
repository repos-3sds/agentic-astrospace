import { Injectable, inject, signal } from '@angular/core';
import { NavigationEnd, NavigationStart, Router } from '@angular/router';
import { filter } from 'rxjs';

/**
 * Whether there is an in-app screen behind the current one.
 *
 * The router does not expose this, and `history.length` counts the pages
 * before the app as well, so every native back arrow was a hard-coded route:
 * Notifications opened from Today went "back" to Settings, Search went to
 * Settings, Muhurta went to Remedies.
 *
 * The count starts at the screen the app launched on. A forward navigation
 * adds one; a system or browser back (popstate) removes one; a navigation
 * that replaces the URL (`replaceUrl`, which the Ask answer screen uses to
 * swap `?pending=1` for `?thread=…`) or skips the location bar adds
 * nothing, because neither adds a history entry. `canGoBack()` is true
 * exactly when `history.back()` stays inside the app.
 *
 * Created eagerly by the root component so the first navigation is
 * counted; a lazily created instance would start at zero on whichever
 * screen first rendered a back arrow.
 */
@Injectable({ providedIn: 'root' })
export class NavigationHistoryService {
  private readonly router = inject(Router);
  private readonly depth = signal(0);
  private delta = 1;

  readonly canGoBack = (): boolean => this.depth() > 1;

  constructor() {
    // With blocking initial navigation the first NavigationEnd fires before
    // the root component (and so this service) exists; count it from the
    // router's own record instead of missing it.
    if (this.router.navigated) this.depth.set(1);
    this.router.events.pipe(filter((event) => event instanceof NavigationStart)).subscribe((event) => {
      const start = event as NavigationStart;
      const extras = this.router.getCurrentNavigation()?.extras;
      this.delta = start.navigationTrigger === 'popstate' ? -1
        : extras?.replaceUrl || extras?.skipLocationChange ? 0
        : 1;
    });
    this.router.events.pipe(filter((event) => event instanceof NavigationEnd)).subscribe(() => {
      // The first completed navigation is the launch screen, whatever its
      // extras say: Angular performs the initial navigation with replaceUrl.
      this.depth.update((depth) => (depth === 0 ? 1 : Math.max(0, depth + this.delta)));
      this.delta = 1;
    });
  }
}
