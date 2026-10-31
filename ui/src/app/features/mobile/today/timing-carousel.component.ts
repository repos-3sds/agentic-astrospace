import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, afterNextRender, effect, inject, input, signal, viewChild } from '@angular/core';
import { RouterLink } from '@angular/router';

/** One card of Today's timing carousel. */
export interface TimingSlide {
  key: string;
  /** good: a kind window; care: one to keep clear of; note: the day's timing note. */
  tone: 'good' | 'care' | 'note';
  eyebrow: string;
  title: string;
  /** "9:06 am to 10:33 am"; empty on the note. */
  time: string;
  detail: string;
  /** "Starts in 40m" / "Ends in 12m". */
  in: string;
}

/** Long enough to read a card twice. */
export const AUTO_ADVANCE_MS = 6000;

/**
 * Today's timings, one card at a time: the day's note, then the windows still
 * ahead, good and careful mixed in time order (Hawk, 2026-10-31). Swipe to
 * move; it also moves on its own every few seconds until the reader touches
 * it, so the text never shifts under someone reading. Still when the phone
 * asks for reduced motion.
 */
@Component({
  selector: 'as-timing-carousel',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './timing-carousel.component.html',
  styleUrl: './timing-carousel.component.scss',
})
export class TimingCarouselComponent {
  readonly slides = input.required<TimingSlide[]>();
  /** The day the cards open in the calendar. */
  readonly date = input<string>('');

  protected readonly index = signal(0);
  private readonly track = viewChild<ElementRef<HTMLElement>>('track');
  private touched = false;
  private timer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    const reduced = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    afterNextRender(() => {
      if (reduced) return;
      this.timer = setInterval(() => this.advance(), AUTO_ADVANCE_MS);
    });
    // A card that passes (its window ended) shortens the list: stay in range.
    effect(() => {
      const count = this.slides().length;
      if (this.index() >= count) this.index.set(Math.max(0, count - 1));
    });
    inject(DestroyRef).onDestroy(() => this.stop());
  }

  /** The reader took over: the carousel stays where they put it. */
  protected stop(): void {
    this.touched = true;
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
  }

  protected go(i: number): void {
    this.stop();
    this.scrollTo(i, 'smooth');
  }

  protected onScroll(): void {
    const offsets = this.offsets();
    if (!offsets.length) return;
    const left = this.track()!.nativeElement.scrollLeft;
    let nearest = 0;
    offsets.forEach((x, i) => { if (Math.abs(x - left) < Math.abs(offsets[nearest] - left)) nearest = i; });
    this.index.set(nearest);
  }

  /** Each card's scroll position: its distance from the first card. */
  private offsets(): number[] {
    const cards = Array.from(this.track()?.nativeElement.children ?? []) as HTMLElement[];
    return cards.map((card) => card.offsetLeft - cards[0].offsetLeft);
  }

  private advance(): void {
    const count = this.slides().length;
    if (this.touched || count < 2) return;
    this.scrollTo((this.index() + 1) % count, 'smooth');
  }

  private scrollTo(i: number, behavior: ScrollBehavior): void {
    const el = this.track()?.nativeElement;
    this.index.set(i);
    if (el) el.scrollTo({ left: this.offsets()[i] ?? 0, behavior });
  }

  protected label(slide: TimingSlide, i: number): string {
    const parts = [slide.eyebrow, slide.title, slide.time, slide.detail, slide.in].filter(Boolean);
    return `${parts.join('. ')}. Timing ${i + 1} of ${this.slides().length}. Open today in the calendar`;
  }
}
