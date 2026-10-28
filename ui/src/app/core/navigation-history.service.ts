import { Injectable, inject, signal } from '@angular/core';
import { Location } from '@angular/common';
import {
  NavigationCancel,
  NavigationCancellationCode,
  NavigationEnd,
  NavigationStart,
  Router,
} from '@angular/router';
import { filter } from 'rxjs';

/** One history entry the app created, as far as the app can tell. */
interface Entry {
  url: string;
  /** Opened by a tab-bar press rather than a link inside a screen. */
  viaTab: boolean;
}

/** Navigation state a tab press carries; read back by the scroll memory. */
export interface TabNavigationState {
  viaTab: true;
  restoreScroll: true;
}

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
 * It also keeps the URL of each entry, so the phone's own back (Android's
 * back, the iPhone edge swipe) can return to the screen that opened this one
 * without walking back out of the tabbed app into onboarding, and a tab press
 * can step back to a screen already in the history instead of stacking a
 * copy of it.
 *
 * Created eagerly by the root component so the first navigation is
 * counted; a lazily created instance would start at zero on whichever
 * screen first rendered a back arrow.
 */
@Injectable({ providedIn: 'root' })
export class NavigationHistoryService {
  private readonly router = inject(Router);
  private readonly location = inject(Location);
  private readonly depth = signal(0);
  private delta = 1;
  private viaTab = false;
  /**
   * An entry pushed by a navigation that a newer one then superseded. Ask
   * removes a handed-off `?q=` while Today → Ask is still finishing: the push
   * to /m/ask?q= has already happened, and the replace that supersedes it
   * must not lose it.
   */
  private carried = 0;
  private pathBefore = '';
  /** entries[i] is the entry at depth i + 1. */
  private readonly entries: Entry[] = [];
  /**
   * Depth of the first screen inside the tabbed shell. Entries below it are
   * the landing page, sign-in and onboarding, which back must never reopen.
   */
  private shellBase = Number.POSITIVE_INFINITY;
  private shellEntering = false;
  /** Set by {@link go}: the next popstate moves this many entries. */
  private pendingJump = 0;

  readonly canGoBack = (): boolean => this.depth() > 1;

  constructor() {
    // With blocking initial navigation the first NavigationEnd fires before
    // the root component (and so this service) exists; count it from the
    // router's own record instead of missing it.
    if (this.router.navigated) {
      this.depth.set(1);
      this.entries[0] = { url: this.router.url, viaTab: false };
    }
    this.router.events.pipe(filter((event) => event instanceof NavigationCancel)).subscribe((event) => {
      const cancel = event as NavigationCancel;
      if (cancel.code !== NavigationCancellationCode.SupersededByNewNavigation) return;
      if (this.delta > 0 && this.location.path(true) !== this.pathBefore) this.carried += this.delta;
    });
    this.router.events.pipe(filter((event) => event instanceof NavigationStart)).subscribe((event) => {
      const start = event as NavigationStart;
      if (!this.carried) this.pathBefore = this.location.path(true);
      const extras = this.router.getCurrentNavigation()?.extras;
      this.viaTab = (extras?.state as Partial<TabNavigationState> | undefined)?.viaTab === true;
      if (start.navigationTrigger === 'popstate') {
        this.delta = this.pendingJump || -1;
        this.pendingJump = 0;
      } else {
        this.delta = extras?.replaceUrl || extras?.skipLocationChange ? 0 : 1;
      }
    });
    this.router.events.pipe(filter((event) => event instanceof NavigationEnd)).subscribe((event) => {
      const end = event as NavigationEnd;
      this.delta += this.carried;
      this.carried = 0;
      const popped = this.delta < 0;
      // The first completed navigation is the launch screen, whatever its
      // extras say: Angular performs the initial navigation with replaceUrl.
      this.depth.update((depth) => (depth === 0 ? 1 : Math.max(1, depth + this.delta)));
      const index = this.depth() - 1;
      if (this.delta > 0) this.entries.length = index;
      const kept = this.entries[index];
      this.entries[index] = {
        url: end.urlAfterRedirects,
        viaTab: popped ? kept?.viaTab ?? false : this.viaTab,
      };
      if (this.shellEntering) {
        this.shellBase = this.depth();
        this.shellEntering = false;
      }
      this.delta = 1;
      this.viaTab = false;
    });
  }

  /** The tabbed shell is being created; its first screen is where back stops. */
  enterShell(): void {
    this.shellEntering = true;
  }

  leaveShell(): void {
    this.shellEntering = false;
    this.shellBase = Number.POSITIVE_INFINITY;
  }

  inShell(): boolean {
    return this.depth() >= this.shellBase;
  }

  /** Whether the current screen was opened by a tab press. */
  currentViaTab(): boolean {
    return this.entries[this.depth() - 1]?.viaTab ?? false;
  }

  /**
   * Steps back (a negative number) to the nearest screen inside the shell
   * that is not the one showing, or null when there is none. Entries of the
   * same screen are skipped, so back never "does nothing".
   */
  stepsBack(): number | null {
    const index = this.depth() - 1;
    const here = pathOf(this.entries[index]?.url ?? this.router.url);
    for (let i = index - 1; i >= this.shellBase - 1 && i >= 0; i--) {
      const entry = this.entries[i];
      if (!entry) return null;
      if (pathOf(entry.url) !== here) return i - index;
    }
    return null;
  }

  /** Steps back to an entry with exactly this URL, inside the shell. */
  stepsBackTo(url: string): number | null {
    const index = this.depth() - 1;
    for (let i = index - 1; i >= this.shellBase - 1 && i >= 0; i--) {
      if (this.entries[i]?.url === url) return i - index;
    }
    return null;
  }

  /** history.go(steps), counted as one popstate of that many entries. */
  go(steps: number): void {
    if (steps === 0) return;
    this.pendingJump = steps;
    this.location.historyGo(steps);
  }
}

function pathOf(url: string): string {
  return url.split('#')[0].split('?')[0] || '/';
}
