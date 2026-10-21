import { Injectable } from '@angular/core';

/** What a screen does when pulled down: fetch fresh data, resolve when shown. */
export type PullRefreshHandler = () => Promise<unknown>;

/**
 * Which screens take pull to refresh, and what each one reloads (audit N13).
 *
 * Handlers are filed by route path rather than by "the last one registered",
 * because tab roots are retained (MobileRouteReuseStrategy): Today stays
 * alive while detached, so a stack of registrations would hand Calendar's
 * pull to Today, or Today's back to a destroyed Calendar. The shell's
 * PullRefreshDirective looks up the path on screen when a pull starts; a
 * screen without a handler simply does not pull.
 */
@Injectable({ providedIn: 'root' })
export class PullRefreshService {
  private readonly handlers = new Map<string, PullRefreshHandler>();

  /** File `handler` under `path` (e.g. '/m/today'); returns the unregister. */
  register(path: string, handler: PullRefreshHandler): () => void {
    this.handlers.set(path, handler);
    return () => {
      if (this.handlers.get(path) === handler) this.handlers.delete(path);
    };
  }

  handlerFor(url: string): PullRefreshHandler | null {
    const path = url.split('#')[0].split('?')[0];
    return this.handlers.get(path) ?? null;
  }
}
