import {
  AfterViewInit,
  AnimationCallbackEvent,
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  inject,
  input,
  output,
  viewChild,
} from '@angular/core';
import { SheetOverlayService } from '../../../core/sheet-overlay.service';

/** How far (px) a drag must travel before release dismisses, at most. */
const DISMISS_DISTANCE = 120;
/** A flick faster than this (px/ms) dismisses whatever the distance. */
const DISMISS_VELOCITY = 0.5;
/** Mirrors --m-dur-slow; the fallback if transitionend never fires. */
const LEAVE_MS = 320;
const SCRIM_OPACITY = 0.38;

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), ' +
  'textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

let nextTitleId = 0;

/**
 * Bottom sheet: scrim plus a rounded panel (Figma nodes 21:23 / 21:24).
 *
 * Shared by every sheet in the app — day-quality detail, why-this-reading,
 * planet detail, provenance, learning — so the scrim opacity, corner radius
 * and handle are defined once and cannot drift between screens.
 *
 * Dismissal is deliberately generous: scrim tap, Escape, the Close button,
 * and (on the host screen) the primary button all close it. A sheet that can
 * only be dismissed by one affordance is a trap on a phone — and until
 * 2026-10-15 the scrim was the only one that worked for a screen-reader or
 * keyboard user, since the scrim is aria-hidden and nothing ever took focus.
 *
 * Accessibility, done here so no consumer has to remember it:
 * - focus moves into the panel on open and back to the opener on close;
 * - Tab cycles within the panel (aria-modal alone does not trap focus);
 * - the dialog is named by its first heading via aria-labelledby, or by
 *   `label` when a consumer has no heading;
 * - a visible 44 px Close button sits in the handle row.
 *
 * Motion, also done here once:
 * - the handle row and any projected <header> drag the panel; release past
 *   DISMISS_DISTANCE (or a downward flick) dismisses, otherwise it springs
 *   back;
 * - every dismissal — including a consumer's own @if turning false — slides
 *   the panel out and fades the scrim through `animate.leave`, instead of
 *   the sheet vanishing in one frame;
 * - scrolling inside the panel never chains to the page behind it.
 */
@Component({
  selector: 'as-sheet',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div #scrim class="scrim" (click)="dismissed.emit()" aria-hidden="true"></div>
    <div
      #panel
      class="panel"
      role="dialog"
      aria-modal="true"
      [attr.aria-label]="label()"
      (keydown.escape)="dismissed.emit()"
      (keydown.tab)="trapTab($event)"
      (keydown.shift.tab)="trapTab($event)"
      (pointerdown)="dragStart($event)"
      (pointermove)="dragMove($event)"
      (pointerup)="dragEnd($event)"
      (pointercancel)="dragCancel()"
      tabindex="-1"
    >
      <div class="handle-row">
        <div class="handle" aria-hidden="true"></div>
        <button class="close" type="button" aria-label="Close" (click)="dismissed.emit()">
          <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
          </svg>
        </button>
      </div>
      <ng-content />
    </div>
  `,
  styleUrl: './sheet.component.scss',
  host: {
    '(animate.leave)': 'leave($event)',
  },
})
export class SheetComponent implements AfterViewInit {
  readonly dismissed = output<void>();
  /** Fallback accessible name, used only when the projected content has no heading. */
  readonly label = input('Details');

  private readonly panel = viewChild.required<ElementRef<HTMLElement>>('panel');
  private readonly scrim = viewChild.required<ElementRef<HTMLElement>>('scrim');
  private opener: HTMLElement | null = null;
  private drag: { id: number; startY: number; dy: number; lastY: number; lastT: number; velocity: number } | null = null;

  constructor() {
    const overlay = inject(SheetOverlayService);
    overlay.push();
    // Lets Android's hardware back button close this sheet instead of falling
    // through to route navigation underneath — see app.ts's backButton listener.
    const unregister = overlay.registerDismiss(() => this.dismissed.emit());
    inject(DestroyRef).onDestroy(() => {
      overlay.pop();
      unregister();
      this.restoreFocus();
    });
  }

  ngAfterViewInit(): void {
    const panel = this.panel().nativeElement;
    this.opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    this.nameFromHeading(panel);
    // The panel itself takes focus rather than the Close button: a screen
    // reader then announces the dialog's name first, and a sighted keyboard
    // user's first Tab lands on Close, which is the right first stop.
    panel.focus({ preventScroll: true });
  }

  /** A drag starts only on the handle row or a projected header, never on a control. */
  protected dragStart(event: PointerEvent): void {
    if (event.button !== 0 || this.drag) return;
    const panel = this.panel().nativeElement;
    const target = event.target as HTMLElement | null;
    if (!target || target.closest('button, a, input, textarea, select, [role="button"]')) return;
    const zone = target.closest('.handle-row, header');
    if (!zone || !panel.contains(zone)) return;
    this.drag = { id: event.pointerId, startY: event.clientY, dy: 0, lastY: event.clientY, lastT: event.timeStamp, velocity: 0 };
    // Capture keeps the moves coming once the finger leaves the header. It
    // throws for a pointer the browser no longer tracks; the drag still works.
    try { panel.setPointerCapture(event.pointerId); } catch { /* see above */ }
    panel.classList.add('is-dragging');
  }

  protected dragMove(event: PointerEvent): void {
    const drag = this.drag;
    if (!drag || event.pointerId !== drag.id) return;
    const raw = event.clientY - drag.startY;
    // Down follows the finger; up resists, so the panel can't be pulled off its edge.
    drag.dy = raw > 0 ? raw : raw / 6;
    const dt = event.timeStamp - drag.lastT;
    // Moves arrive about once a frame; two closer than 4 ms say nothing
    // reliable about speed.
    if (dt > 4) drag.velocity = (event.clientY - drag.lastY) / dt;
    drag.lastY = event.clientY;
    drag.lastT = event.timeStamp;
    const panel = this.panel().nativeElement;
    panel.style.transform = `translateY(${drag.dy}px)`;
    const progress = Math.max(0, Math.min(1, drag.dy / Math.max(panel.offsetHeight, 1)));
    this.scrim().nativeElement.style.opacity = String(SCRIM_OPACITY * (1 - progress));
  }

  protected dragEnd(event: PointerEvent): void {
    const drag = this.drag;
    if (!drag || event.pointerId !== drag.id) return;
    this.drag = null;
    const panel = this.panel().nativeElement;
    panel.classList.remove('is-dragging');
    try { panel.releasePointerCapture(event.pointerId); } catch { /* not captured */ }
    const threshold = Math.min(DISMISS_DISTANCE, panel.offsetHeight * 0.3);
    if (drag.dy > threshold || (drag.dy > 12 && drag.velocity > DISMISS_VELOCITY)) {
      this.dismissed.emit();
    } else {
      this.springBack();
    }
  }

  protected dragCancel(): void {
    if (!this.drag) return;
    this.drag = null;
    this.panel().nativeElement.classList.remove('is-dragging');
    this.springBack();
  }

  /**
   * `animate.leave` on the host: Angular keeps the element until
   * animationComplete(), so the slide-out runs whichever path removed the
   * sheet. It starts from wherever a drag left the panel.
   */
  protected leave(event: AnimationCallbackEvent): void {
    const panel = this.panel().nativeElement;
    const scrim = this.scrim().nativeElement;
    const reduced = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduced || !panel.isConnected) {
      event.animationComplete();
      return;
    }
    (event.target as HTMLElement).classList.add('is-leaving');
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      panel.removeEventListener('transitionend', onEnd);
      event.animationComplete();
    };
    const onEnd = (e: TransitionEvent) => {
      if (e.target === panel && e.propertyName === 'transform') finish();
    };
    const timer = setTimeout(finish, LEAVE_MS + 80);
    panel.addEventListener('transitionend', onEnd);
    // Pin the current position (mid-drag or at rest) before transitioning out.
    const current = getComputedStyle(panel).transform;
    panel.style.animation = 'none';
    panel.style.transform = current === 'none' ? 'translateY(0)' : current;
    scrim.style.animation = 'none';
    scrim.style.opacity = getComputedStyle(scrim).opacity;
    void panel.offsetHeight;
    panel.style.transform = 'translateY(100%)';
    scrim.style.opacity = '0';
  }

  private springBack(): void {
    const panel = this.panel().nativeElement;
    panel.style.transform = '';
    this.scrim().nativeElement.style.opacity = '';
  }

  protected trapTab(event: Event): void {
    const keyboard = event as KeyboardEvent;
    const items = this.focusable();
    if (!items.length) {
      keyboard.preventDefault();
      return;
    }
    const first = items[0];
    const last = items[items.length - 1];
    const active = document.activeElement;
    if (keyboard.shiftKey && (active === first || active === this.panel().nativeElement)) {
      keyboard.preventDefault();
      last.focus();
    } else if (!keyboard.shiftKey && active === last) {
      keyboard.preventDefault();
      first.focus();
    }
  }

  private focusable(): HTMLElement[] {
    return Array.from(this.panel().nativeElement.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
      (el) => el.offsetParent !== null || el === document.activeElement,
    );
  }

  /** aria-labelledby from the first projected heading; the Close button's own label is skipped. */
  private nameFromHeading(panel: HTMLElement): void {
    const heading = panel.querySelector<HTMLElement>('h1, h2, h3');
    if (!heading) return;
    if (!heading.id) heading.id = `as-sheet-title-${++nextTitleId}`;
    panel.setAttribute('aria-labelledby', heading.id);
    panel.removeAttribute('aria-label');
  }

  private restoreFocus(): void {
    const opener = this.opener;
    this.opener = null;
    if (opener && opener.isConnected && document.activeElement !== opener) {
      opener.focus({ preventScroll: true });
    }
  }
}
