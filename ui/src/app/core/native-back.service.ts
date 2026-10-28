import { Injectable, inject } from '@angular/core';
import { Location } from '@angular/common';
import { Router } from '@angular/router';
import { App as CapacitorApp } from '@capacitor/app';

import { NavigationHistoryService } from './navigation-history.service';
import { SheetOverlayService } from './sheet-overlay.service';
import { activeTabRoots } from './tab-roots';

/**
 * Routes where Android back puts the app in the background instead of
 * navigating. /m/start is the signed-out landing; /m/today is the main home.
 */
export const NATIVE_EXIT_ROUTES = ['/m/today', '/m/start'];

/**
 * The phone's own back: Android's back button and gesture, and the iPhone's
 * swipe from the left edge. There is no back button on the tabbed screens
 * (Hawk, 2026-10-28); these are how a reader gets back to where they were.
 *
 * Back returns to the screen that opened this one: Today's suggested
 * question opens Ask, and back from Ask (or its answer) is Today again, at
 * the spot the reader left it (the shell's scroll memory restores it on a
 * popstate). A tab root opened from the tab bar has nothing of its own
 * behind it; there Android goes to Today and then backgrounds the app
 * (Material's top-level rule, nativeness audit N11), and the iPhone does
 * nothing, as in any iOS app.
 */
@Injectable({ providedIn: 'root' })
export class NativeBackService {
  private readonly router = inject(Router);
  private readonly location = inject(Location);
  private readonly history = inject(NavigationHistoryService);
  private readonly sheets = inject(SheetOverlayService);

  /** Whether an iPhone edge swipe here would go anywhere. */
  canSwipeBack(): boolean {
    if (this.sheets.open()) return false;
    if (this.popSteps() !== null) return true;
    return this.history.inShell() && !this.atTabRoot();
  }

  /** The iPhone edge swipe, once it has been dragged far enough. */
  swipeBack(): void {
    if (this.pop()) return;
    if (this.history.inShell() && !this.atTabRoot()) {
      void this.router.navigateByUrl('/m/today', { replaceUrl: true });
    }
  }

  /** Android's back button or back gesture. */
  hardwareBack(): void {
    // A sheet is the thing being looked at; close it rather than navigating
    // the route underneath.
    if (this.sheets.dismissTop()) return;
    if (this.pop()) return;
    const path = this.path();
    if (NATIVE_EXIT_ROUTES.includes(path)) {
      // Background, not exit: Android's own convention at an app's root, and
      // it keeps the process (and the decrypted cache) warm for the next
      // open. This replaced a PrimeNG "Close the app?" dialog, which was the
      // only reason the native root pulled PrimeNG in at all.
      void CapacitorApp.minimizeApp();
      return;
    }
    // Tab taps replace the URL, so from a tab other than Today the entry
    // underneath is whatever came before the tabs. Go to Today instead; so
    // does a screen opened straight from a notification or widget.
    if (this.atTabRoot() || this.history.inShell()) {
      void this.router.navigateByUrl('/m/today', { replaceUrl: true });
      return;
    }
    // Outside the tabs (sign-in, onboarding): Angular's Location, not
    // Capacitor's default, so this pops one entry the way an in-app back
    // affordance would, rather than falling through to the WebView's history.
    this.location.back();
  }

  /**
   * Back to the screen that opened this one, when there is one inside the
   * tabs. A tab root that the tab bar opened is the top of its tab: what is
   * behind it belongs to another tab, so it is not popped to.
   */
  private pop(): boolean {
    const steps = this.popSteps();
    if (steps === null) return false;
    this.history.go(steps);
    return true;
  }

  private popSteps(): number | null {
    if (!this.history.inShell()) return null;
    if (this.atTabRoot() && this.history.currentViaTab()) return null;
    return this.history.stepsBack();
  }

  private atTabRoot(): boolean {
    return activeTabRoots().includes(this.path());
  }

  private path(): string {
    return this.router.url.split('?')[0].split('#')[0];
  }
}
