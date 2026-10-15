import {
  AfterViewInit,
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
 */
@Component({
  selector: 'as-sheet',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="scrim" (click)="dismissed.emit()" aria-hidden="true"></div>
    <div
      #panel
      class="panel"
      role="dialog"
      aria-modal="true"
      [attr.aria-label]="label()"
      (keydown.escape)="dismissed.emit()"
      (keydown.tab)="trapTab($event)"
      (keydown.shift.tab)="trapTab($event)"
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
})
export class SheetComponent implements AfterViewInit {
  readonly dismissed = output<void>();
  /** Fallback accessible name, used only when the projected content has no heading. */
  readonly label = input('Details');

  private readonly panel = viewChild.required<ElementRef<HTMLElement>>('panel');
  private opener: HTMLElement | null = null;

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
