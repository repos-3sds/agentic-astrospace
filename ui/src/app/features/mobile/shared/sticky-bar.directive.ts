import { AfterViewInit, DestroyRef, Directive, ElementRef, NgZone, inject, input } from '@angular/core';

/** The scrollers a screen can sit in: the shell's content, or wide Settings' list pane. */
const SCROLLER = 'main.content, .pane-list';

/**
 * Keeps a screen's top bar (back link, or a tab's title row) fixed while the
 * page scrolls under it, as native screens do (Hawk, 2026-10-30).
 *
 * Every /m screen scrolls inside the shell's one scroller, so the bar is made
 * `position: sticky` there (styles-mobile.scss, `.m-sticky-bar`), not fixed: it
 * stays in the flow, scroll memory and pull to refresh are untouched, and
 * tablets' panes keep working. Once the page has moved, the bar takes a frosted
 * ground so text passes under it legibly.
 *
 * When the screen's big serif title (its first h1 outside the bar) has slid up
 * under the bar, the bar shows that title small and centred in place of the
 * parent's name: the iOS large-title pattern. A bar that holds its own h1
 * (Calendar, Settings) never needs this. Pass a title to override the h1.
 */
@Directive({
  selector: '[asStickyBar]',
  standalone: true,
  host: { class: 'm-sticky-bar' },
})
export class StickyBarDirective implements AfterViewInit {
  /** The small title to show once the big one has scrolled away; '' reads the screen's h1. */
  readonly asStickyBar = input<string | ''>('');

  private readonly bar = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;
  private readonly zone = inject(NgZone);
  private readonly destroyRef = inject(DestroyRef);

  ngAfterViewInit(): void {
    const scroller = this.bar.closest<HTMLElement>(SCROLLER);
    if (!scroller) return;
    let frame = 0;
    const update = () => {
      frame = 0;
      this.update(scroller);
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    this.zone.runOutsideAngular(() => {
      scroller.addEventListener('scroll', schedule, { passive: true });
      // A screen restored to an earlier offset, or one whose content arrives
      // late, is checked once its first frames have settled.
      schedule();
    });
    this.destroyRef.onDestroy(() => {
      scroller.removeEventListener('scroll', schedule);
      if (frame) cancelAnimationFrame(frame);
    });
  }

  private update(scroller: HTMLElement): void {
    const bar = this.bar;
    bar.classList.toggle('is-scrolled', scroller.scrollTop > 2);
    const heading = this.heading(scroller);
    const title = this.asStickyBar() || heading?.textContent?.trim() || '';
    const collapsed =
      !!title && !!heading && heading.getBoundingClientRect().bottom <= bar.getBoundingClientRect().bottom;
    if (title) bar.setAttribute('data-title', title);
    bar.classList.toggle('is-collapsed', collapsed);
  }

  /** The screen's big title: its first visible h1 that is not inside the bar. */
  private heading(scroller: HTMLElement): HTMLElement | null {
    if (this.bar.querySelector('h1')) return null;
    let screen: HTMLElement = this.bar;
    while (screen.parentElement && screen.parentElement !== scroller) screen = screen.parentElement;
    for (const h1 of Array.from(screen.querySelectorAll<HTMLElement>('h1'))) {
      if (!this.bar.contains(h1) && h1.getClientRects().length) return h1;
    }
    return null;
  }
}
