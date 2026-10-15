import { DestroyRef, Directive, ElementRef, inject } from '@angular/core';
import { NavigationEnd, NavigationStart, Router } from '@angular/router';
import { RETAINED_MOBILE_TABS } from '../../../core/mobile-route-reuse-strategy';

/** How long a restore keeps retrying while a rebuilt screen loads its content. */
const RESTORE_WINDOW_MS = 1500;
/** Positions remembered at once; the oldest is dropped past this. */
const MAX_ENTRIES = 60;

/**
 * Scroll memory for the shell's single scroller.
 *
 * Every /m screen renders inside the shell's `main.content`, so the window
 * never scrolls and the router's own `withInMemoryScrolling` has nothing to
 * act on. Without this, the one scroller kept whatever offset the previous
 * screen left: Today scrolled to the bottom opened Explore at its bottom, and
 * every return to a tab or back from a detail landed at the top.
 *
 * The rule is the native one:
 * - leaving a screen remembers its offset, keyed by URL;
 * - back (popstate) restores the offset of the screen returned to;
 * - a retained tab root (MobileRouteReuseStrategy) re-attaching restores
 *   where it was, whichever way it was reached;
 * - any other forward navigation starts at the top;
 * - a navigation that only changes the query string on the same screen
 *   (a date, a segment) leaves the offset alone.
 *
 * A screen rebuilt on back loads its content asynchronously, so a restore
 * keeps re-applying for a short window until the content is tall enough. A
 * touch or wheel cancels it: the reader's own scroll always wins.
 */
@Directive({
  selector: '[asScrollMemory]',
  standalone: true,
  exportAs: 'asScrollMemory',
})
export class ScrollMemoryDirective {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;
  private readonly router = inject(Router);
  private readonly positions = new Map<string, number>();
  /**
   * The URL on screen, tracked from NavigationEnd rather than read from
   * `router.url` at NavigationStart, so the offset being saved is always filed
   * under the screen that was actually showing — never under the destination
   * of a popstate or a redirect.
   */
  private currentUrl = '';
  private fromPath = '';
  private popstate = false;
  private frame = 0;

  constructor() {
    const sub = this.router.events.subscribe((event) => {
      if (event instanceof NavigationStart) {
        this.cancelRestore();
        const leaving = this.currentUrl || this.router.url;
        this.fromPath = pathOf(leaving);
        this.remember(this.keyFor(leaving), this.host.scrollTop);
        this.popstate = event.navigationTrigger === 'popstate';
      } else if (event instanceof NavigationEnd) {
        this.currentUrl = event.urlAfterRedirects;
        this.settle(event.urlAfterRedirects);
      }
    });
    const cancel = () => this.cancelRestore();
    const opts: AddEventListenerOptions = { passive: true };
    this.host.addEventListener('touchstart', cancel, opts);
    this.host.addEventListener('wheel', cancel, opts);
    inject(DestroyRef).onDestroy(() => {
      sub.unsubscribe();
      this.cancelRestore();
      this.host.removeEventListener('touchstart', cancel);
      this.host.removeEventListener('wheel', cancel);
    });
  }

  /** The active tab tapped again: back to the top, as every native tab bar does. */
  scrollToTop(): void {
    this.cancelRestore();
    const smooth = !globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (typeof this.host.scrollTo === 'function') {
      this.host.scrollTo({ top: 0, behavior: smooth ? 'smooth' : 'auto' });
    } else {
      this.host.scrollTop = 0;
    }
  }

  private settle(url: string): void {
    const path = pathOf(url);
    if (path === this.fromPath) return;
    const saved = this.positions.get(this.keyFor(url));
    const restore = saved !== undefined && (this.popstate || isRetainedTab(path));
    this.popstate = false;
    if (restore && saved > 0) {
      this.restore(saved);
    } else {
      this.host.scrollTop = 0;
    }
  }

  private restore(target: number): void {
    const started = performance.now();
    const apply = () => {
      this.host.scrollTop = target;
      const reached = Math.abs(this.host.scrollTop - target) <= 1;
      if (reached || performance.now() - started > RESTORE_WINDOW_MS) {
        this.frame = 0;
        return;
      }
      this.frame = requestAnimationFrame(apply);
    };
    apply();
  }

  private cancelRestore(): void {
    if (this.frame) cancelAnimationFrame(this.frame);
    this.frame = 0;
  }

  private remember(key: string, top: number): void {
    this.positions.delete(key);
    this.positions.set(key, top);
    if (this.positions.size > MAX_ENTRIES) {
      const oldest = this.positions.keys().next().value;
      if (oldest !== undefined) this.positions.delete(oldest);
    }
  }

  /** Tab roots by path (their query string is transient); details by full URL. */
  private keyFor(url: string): string {
    const path = pathOf(url);
    return isRetainedTab(path) ? path : url;
  }
}

function pathOf(url: string): string {
  return url.split('#')[0].split('?')[0] || '/';
}

function isRetainedTab(path: string): boolean {
  return RETAINED_MOBILE_TABS.has(path.replace(/^\//, ''));
}
