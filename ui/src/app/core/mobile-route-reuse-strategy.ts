import { RouteReuseStrategy, ActivatedRouteSnapshot, DetachedRouteHandle } from '@angular/router';
import { Injectable } from '@angular/core';

@Injectable()
export class MobileRouteReuseStrategy implements RouteReuseStrategy {
  private handlers: { [key: string]: DetachedRouteHandle } = {};
  private readonly retainedTabs = new Set([
    'm/today',
    'm/ask',
    'm/explore',
    'm/chart',
    'm/chart/periods',
    'm/calendar',
    'm/settings',
  ]);

  shouldDetach(route: ActivatedRouteSnapshot): boolean {
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
