import { DestroyRef, Directive, ElementRef, inject } from '@angular/core';
import { Router } from '@angular/router';
import { HapticsService } from '../../../core/haptics.service';
import { PullRefreshService } from '../../../core/pull-refresh.service';
import { SheetOverlayService } from '../../../core/sheet-overlay.service';

/** Finger travel, after resistance, that arms a refresh. */
export const PULL_THRESHOLD = 64;
/** The furthest the indicator travels, however far the finger goes. */
const PULL_MAX = 96;
/** Finger pixels per indicator pixel: the pull feels heavier than a scroll. */
const RESISTANCE = 0.5;
/** Movement before the gesture decides whether it is a pull at all. */
const SLOP = 8;
/** The spinner stays at least this long, so a cached answer still reads as "refreshed". */
const MIN_SPIN_MS = 450;

/**
 * Pull to refresh for the shell's scroller (audit N13).
 *
 * Android-style: the page does not move; a round indicator drops from under
 * the top edge and its arc fills as the finger travels. Moving the page
 * itself would mean a transform on the scroller, which turns Today's
 * position: fixed sky into a box-relative layer (the trap noted in the shell
 * SCSS for -webkit-overflow-scrolling).
 *
 * A pull starts only when the scroller is already at the top, the screen on
 * show has a handler in PullRefreshService, no sheet is open, and the first
 * movement is clearly downward rather than sideways (Calendar's month swipe).
 * Touch only, so desktop and mouse users never see it. Listeners stay
 * passive: at scrollTop 0 a downward drag has nothing to scroll, and
 * overscroll-behavior on the scroller already stops the WebView's own glow
 * from chaining to the page.
 */
@Directive({
  selector: '[asPullRefresh]',
  standalone: true,
})
export class PullRefreshDirective {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;
  private readonly router = inject(Router);
  private readonly registry = inject(PullRefreshService);
  private readonly sheets = inject(SheetOverlayService);
  private readonly haptics = inject(HapticsService);

  private indicator: HTMLElement | null = null;
  private startX = 0;
  private startY = 0;
  private state: 'idle' | 'deciding' | 'pulling' | 'refreshing' = 'idle';
  private distance = 0;
  private armed = false;

  constructor() {
    const opts: AddEventListenerOptions = { passive: true };
    const start = (event: TouchEvent) => this.onStart(event);
    const move = (event: TouchEvent) => this.onMove(event);
    const end = () => this.onEnd();
    this.host.addEventListener('touchstart', start, opts);
    this.host.addEventListener('touchmove', move, opts);
    this.host.addEventListener('touchend', end, opts);
    this.host.addEventListener('touchcancel', end, opts);
    inject(DestroyRef).onDestroy(() => {
      this.host.removeEventListener('touchstart', start);
      this.host.removeEventListener('touchmove', move);
      this.host.removeEventListener('touchend', end);
      this.host.removeEventListener('touchcancel', end);
      this.indicator?.remove();
    });
  }

  private onStart(event: TouchEvent): void {
    if (this.state === 'refreshing' || event.touches.length !== 1) return;
    if (this.host.scrollTop > 0 || this.sheets.open()) return;
    if (!this.registry.handlerFor(this.router.url)) return;
    const touch = event.touches[0];
    this.startX = touch.clientX;
    this.startY = touch.clientY;
    this.state = 'deciding';
  }

  private onMove(event: TouchEvent): void {
    if (this.state !== 'deciding' && this.state !== 'pulling') return;
    const touch = event.touches[0];
    const dx = touch.clientX - this.startX;
    const dy = touch.clientY - this.startY;
    if (this.state === 'deciding') {
      if (Math.abs(dx) < SLOP && Math.abs(dy) < SLOP) return;
      // Upward, sideways, or the page has scrolled under the finger: not a pull.
      if (dy <= 0 || Math.abs(dx) > Math.abs(dy) || this.host.scrollTop > 0) {
        this.state = 'idle';
        return;
      }
      this.state = 'pulling';
    }
    this.distance = Math.min(PULL_MAX, Math.max(0, dy * RESISTANCE));
    const armed = this.distance >= PULL_THRESHOLD;
    if (armed && !this.armed) this.haptics.select();
    this.armed = armed;
    this.paint(this.distance, false);
  }

  private onEnd(): void {
    if (this.state === 'deciding') {
      this.state = 'idle';
      return;
    }
    if (this.state !== 'pulling') return;
    if (!this.armed) {
      this.state = 'idle';
      this.hide();
      return;
    }
    const handler = this.registry.handlerFor(this.router.url);
    if (!handler) {
      this.state = 'idle';
      this.hide();
      return;
    }
    void this.run(handler);
  }

  private async run(handler: () => Promise<unknown>): Promise<void> {
    this.state = 'refreshing';
    this.paint(PULL_THRESHOLD, true);
    const started = performance.now();
    try {
      await handler();
    } catch {
      // A screen shows its own error state; the indicator only has to let go.
    }
    const left = MIN_SPIN_MS - (performance.now() - started);
    if (left > 0) await new Promise((done) => setTimeout(done, left));
    this.state = 'idle';
    this.armed = false;
    this.hide();
  }

  private paint(distance: number, spinning: boolean): void {
    const el = this.ensureIndicator();
    const progress = Math.min(1, distance / PULL_THRESHOLD);
    el.classList.add('is-visible');
    el.classList.toggle('is-spinning', spinning);
    el.classList.toggle('is-armed', progress >= 1);
    el.style.setProperty('--pull-y', `${distance}px`);
    el.style.setProperty('--pull-progress', String(progress));
    el.setAttribute('aria-hidden', spinning ? 'false' : 'true');
  }

  private hide(): void {
    const el = this.indicator;
    if (!el) return;
    el.classList.remove('is-visible', 'is-spinning', 'is-armed');
    el.style.setProperty('--pull-y', '0px');
    el.setAttribute('aria-hidden', 'true');
  }

  /**
   * The indicator sits beside the scroller, not inside it, so it never
   * scrolls or takes part in scroll anchoring. Styled in styles-mobile.scss:
   * an element made here carries no component encapsulation attribute.
   */
  private ensureIndicator(): HTMLElement {
    if (this.indicator) return this.indicator;
    const el = document.createElement('div');
    el.className = 'm-pull-refresh';
    el.setAttribute('role', 'status');
    el.setAttribute('aria-label', 'Refreshing');
    el.setAttribute('aria-hidden', 'true');
    el.innerHTML = '<span class="m-pull-refresh-arc"></span>';
    (this.host.parentElement ?? this.host).appendChild(el);
    this.indicator = el;
    return el;
  }
}
