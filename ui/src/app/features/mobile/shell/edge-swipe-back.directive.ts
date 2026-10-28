import { DestroyRef, Directive, ElementRef, inject, input } from '@angular/core';

import { NativeBackService } from '../../../core/native-back.service';

/** How far from the left edge a touch must start to be a back swipe. */
const EDGE_PX = 24;
/** Movement before the gesture decides whether it is sideways. */
const DECIDE_PX = 10;
/** Released past this share of the width, the swipe goes back. */
const COMMIT_SHARE = 0.35;
/** Or a flick faster than this (px per ms) to the right. */
const COMMIT_SPEED = 0.5;
const SETTLE_MS = 180;

/**
 * The iPhone's swipe from the left edge, for the tabbed shell.
 *
 * WKWebView has its own back-forward swipe (allowsBackForwardNavigationGestures),
 * but it walks the WebView's raw history: past the first tab, out through
 * onboarding and sign-in. It is left off, and this does the same gesture
 * with the app's own idea of back (NativeBackService), so a swipe from Ask
 * returns to the Today it was opened from, at the same spot.
 *
 * The screen follows the finger as UIKit's does; released past a third of
 * the width or flicked, it slides off and the previous screen comes back,
 * otherwise it settles where it was. A touch that starts away from the edge,
 * moves mostly up or down, or starts where back goes nowhere is left alone.
 *
 * `target` is the element that moves (the shell's panes); the listeners sit
 * on the host in the capture phase, so a horizontal swipe inside the page
 * (Calendar's months) does not also see an edge swipe as its own.
 */
@Directive({
  selector: '[asEdgeSwipeBack]',
  standalone: true,
})
export class EdgeSwipeBackDirective {
  readonly asEdgeSwipeBack = input(false);
  readonly swipeTarget = input<HTMLElement | null>(null);

  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;
  private readonly back = inject(NativeBackService);

  private startX = 0;
  private startY = 0;
  private lastX = 0;
  private lastT = 0;
  private speed = 0;
  /** null: not decided yet; true: this touch is a back swipe; false: it is not. */
  private engaged: boolean | null = false;

  constructor() {
    const start = (event: TouchEvent) => this.onStart(event);
    const move = (event: TouchEvent) => this.onMove(event);
    const end = (event: TouchEvent) => this.onEnd(event);
    const capture = { capture: true };
    this.host.addEventListener('touchstart', start, { capture: true, passive: true });
    this.host.addEventListener('touchmove', move, { capture: true, passive: false });
    this.host.addEventListener('touchend', end, capture);
    this.host.addEventListener('touchcancel', end, capture);
    inject(DestroyRef).onDestroy(() => {
      this.host.removeEventListener('touchstart', start, capture);
      this.host.removeEventListener('touchmove', move, capture);
      this.host.removeEventListener('touchend', end, capture);
      this.host.removeEventListener('touchcancel', end, capture);
      this.reset();
    });
  }

  private onStart(event: TouchEvent): void {
    this.engaged = false;
    if (!this.asEdgeSwipeBack() || event.touches.length !== 1) return;
    const touch = event.touches[0];
    if (touch.clientX > EDGE_PX || !this.back.canSwipeBack()) return;
    this.startX = this.lastX = touch.clientX;
    this.startY = touch.clientY;
    this.lastT = event.timeStamp;
    this.speed = 0;
    this.engaged = null;
  }

  private onMove(event: TouchEvent): void {
    if (this.engaged === false) return;
    const touch = event.touches[0];
    if (!touch) return;
    const dx = touch.clientX - this.startX;
    const dy = touch.clientY - this.startY;
    if (this.engaged === null) {
      if (Math.abs(dx) < DECIDE_PX && Math.abs(dy) < DECIDE_PX) return;
      this.engaged = dx > 0 && Math.abs(dx) > Math.abs(dy);
      if (!this.engaged) return;
    }
    event.preventDefault();
    event.stopPropagation();
    const elapsed = event.timeStamp - this.lastT;
    if (elapsed > 0) this.speed = (touch.clientX - this.lastX) / elapsed;
    this.lastX = touch.clientX;
    this.lastT = event.timeStamp;
    this.move(Math.max(0, dx), false);
  }

  private onEnd(event: TouchEvent): void {
    if (!this.engaged) {
      this.engaged = false;
      return;
    }
    this.engaged = false;
    event.stopPropagation();
    const width = this.host.clientWidth || window.innerWidth;
    const dx = Math.max(0, this.lastX - this.startX);
    if (dx > width * COMMIT_SHARE || (this.speed > COMMIT_SPEED && dx > DECIDE_PX)) {
      this.commit(width);
    } else {
      this.move(0, true);
      setTimeout(() => this.reset(), SETTLE_MS);
    }
  }

  private commit(width: number): void {
    const root = document.documentElement;
    const done = () => {
      // The screen has already slid away under the finger; the router's own
      // slide would play it a second time.
      root.dataset['swipeBack'] = '1';
      this.back.swipeBack();
      // The previous screen renders in the panes' place; give it a frame
      // before the slid-off transform comes off.
      setTimeout(() => {
        this.reset();
        delete root.dataset['swipeBack'];
      }, 60);
    };
    if (reducedMotion()) {
      done();
      return;
    }
    this.move(width, true);
    setTimeout(done, SETTLE_MS);
  }

  private move(x: number, animate: boolean): void {
    const target = this.swipeTarget();
    if (!target) return;
    target.style.transition = animate ? `transform ${SETTLE_MS}ms cubic-bezier(0.2, 0.8, 0.2, 1)` : 'none';
    target.style.transform = x ? `translate3d(${x}px, 0, 0)` : '';
    target.classList.toggle('is-swiping-back', x > 0);
  }

  private reset(): void {
    const target = this.swipeTarget();
    if (!target) return;
    target.style.transition = '';
    target.style.transform = '';
    target.classList.remove('is-swiping-back');
  }
}

function reducedMotion(): boolean {
  return !!globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
}
