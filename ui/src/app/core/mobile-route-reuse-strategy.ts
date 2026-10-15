import { RouteReuseStrategy, ActivatedRouteSnapshot, DetachedRouteHandle } from '@angular/router';
import { ComponentRef, Injectable, inject } from '@angular/core';

import { SessionTeardown } from './session-teardown';

/** Angular's DetachedRouteHandle is opaque; this is the part it always carries. */
interface HandleWithComponent {
  componentRef?: ComponentRef<unknown>;
}

/**
 * Footer destinations whose screens are kept alive between visits. Shared
 * with the shell's scroll memory, which restores a retained tab's offset when
 * it re-attaches.
 */
export const RETAINED_MOBILE_TABS: ReadonlySet<string> = new Set([
  'm/today',
  'm/ask',
  'm/explore',
  'm/chart',
  'm/chart/periods',
  'm/calendar',
  'm/settings',
]);

@Injectable()
export class MobileRouteReuseStrategy implements RouteReuseStrategy {
  private handlers: { [key: string]: DetachedRouteHandle } = {};
  private readonly retainedTabs = RETAINED_MOBILE_TABS;
  /**
   * Set by a sign-out, cleared when the native shell is next entered. While
   * set nothing is retained, so the tab being left as the person signs out is
   * destroyed rather than parked for whoever signs in next.
   */
  private purging = false;

  constructor() {
    inject(SessionTeardown, { optional: true })?.register(() => this.clear());
  }

  /**
   * Forget every retained tab view. Stored views are destroyed now; one that
   * is on screen is only dropped from the map, and is destroyed by the router
   * when the sign-out navigation leaves it (shouldDetach is false while
   * purging).
   */
  clear(): void {
    for (const handle of Object.values(this.handlers)) {
      const ref = (handle as HandleWithComponent | null)?.componentRef;
      if (!ref) continue;
      const element = ref.location?.nativeElement as Element | undefined;
      if (element?.isConnected) continue;
      try {
        ref.destroy();
      } catch {
        // Already destroyed with its parent; nothing left to release.
      }
    }
    this.handlers = {};
    this.purging = true;
  }

  shouldDetach(route: ActivatedRouteSnapshot): boolean {
    if (this.purging) return false;
    // Retain only footer destinations. Caching every /m/* detail route kept
    // stale profile/date state alive and grew the handle map for the entire
    // session; detail screens should be rebuilt from their route parameters.
    return this.retainedTabs.has(this.getRoutePath(route));
  }

  store(route: ActivatedRouteSnapshot, handle: DetachedRouteHandle): void {
    if (handle) {
      this.handlers[this.getRoutePath(route)] = handle;
    }
  }

  shouldAttach(route: ActivatedRouteSnapshot): boolean {
    // Re-entering the native shell means a session is in place again.
    if (route.routeConfig?.path === 'm') this.purging = false;
    return !!route.routeConfig && !!this.handlers[this.getRoutePath(route)];
  }

  retrieve(route: ActivatedRouteSnapshot): DetachedRouteHandle | null {
    if (!route.routeConfig) return null;
    return this.handlers[this.getRoutePath(route)] || null;
  }

  shouldReuseRoute(future: ActivatedRouteSnapshot, curr: ActivatedRouteSnapshot): boolean {
    return future.routeConfig === curr.routeConfig;
  }

  private getRoutePath(route: ActivatedRouteSnapshot): string {
    const segments = [];
    let current = route;
    while (current) {
      if (current.url.length > 0) {
        segments.push(current.url.map(s => s.path).join('/'));
      }
      current = current.parent!;
    }
    return segments.reverse().join('/');
  }
}
