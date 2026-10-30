import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  input,
  signal,
} from '@angular/core';

interface Tip {
  /** Where to point; a tip whose target is not on screen is left out. */
  target: string;
  title: string;
  detail: string;
}

interface Spot {
  tip: Tip;
  top: number;
  left: number;
  width: number;
  height: number;
  /** The card goes below the target when there is room, above when not. */
  below: boolean;
}

/** Set by the reveal at the end of setup; read here once. */
export const TODAY_TIPS_KEY = 'siddha.todayTips';

export function queueTodayTips(): void {
  try {
    if (localStorage.getItem(TODAY_TIPS_KEY) !== 'seen') localStorage.setItem(TODAY_TIPS_KEY, 'pending');
  } catch {
    // No storage, no tips; Today works the same.
  }
}

function tipsPending(): boolean {
  try {
    return localStorage.getItem(TODAY_TIPS_KEY) === 'pending';
  } catch {
    return false;
  }
}

/**
 * Three tips on the first visit to Today after setup (onboarding plan
 * 2026-10-30): the day score, Listen to your day, and the tab bar. Tap
 * anywhere for the next one; Skip ends them. Shown once, never again.
 */
@Component({
  selector: 'as-first-visit-tips',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (spot(); as s) {
      <div class="veil" role="dialog" aria-modal="true" [attr.aria-label]="s.tip.title" (click)="next()">
        <span class="ring" [style.top.px]="s.top - 6" [style.left.px]="s.left - 6"
              [style.width.px]="s.width + 12" [style.height.px]="s.height + 12"></span>
        <div class="card" [class.above]="!s.below"
             [style.top.px]="s.below ? s.top + s.height + 18 : null"
             [style.bottom.px]="s.below ? null : viewportHeight() - s.top + 18">
          <p class="count">{{ step() + 1 }} of {{ shown().length }}</p>
          <p class="title">{{ s.tip.title }}</p>
          <p class="detail">{{ s.tip.detail }}</p>
          <div class="row">
            <button type="button" class="skip" (click)="$event.stopPropagation(); done()">Skip</button>
            <button type="button" class="go" (click)="$event.stopPropagation(); next()">
              {{ step() + 1 < shown().length ? 'Next' : 'Got it' }}
            </button>
          </div>
        </div>
      </div>
    }
  `,
  styleUrl: './first-visit-tips.component.scss',
})
export class FirstVisitTipsComponent implements AfterViewInit {
  /** Guided readers see a sentence instead of the score ring. */
  readonly guided = input(false);

  protected readonly step = signal(0);
  protected readonly shown = signal<Tip[]>([]);
  protected readonly spot = signal<Spot | null>(null);
  protected readonly viewportHeight = signal(innerHeight);
  private readonly destroyRef = inject(DestroyRef);

  ngAfterViewInit(): void {
    if (!tipsPending()) return;
    // Let Today lay out (cards, gauge animation) before measuring.
    const timer = setTimeout(() => this.start(), 900);
    const onResize = () => this.place();
    addEventListener('resize', onResize);
    this.destroyRef.onDestroy(() => {
      clearTimeout(timer);
      removeEventListener('resize', onResize);
    });
  }

  protected next(): void {
    if (this.step() + 1 >= this.shown().length) {
      this.done();
      return;
    }
    this.step.update((n) => n + 1);
    this.place();
  }

  protected done(): void {
    this.spot.set(null);
    try {
      localStorage.setItem(TODAY_TIPS_KEY, 'seen');
    } catch {
      // Nothing to remember it in; it will not be queued again anyway.
    }
  }

  private start(): void {
    const tips: Tip[] = [
      this.guided()
        ? { target: '.verdict-guided', title: 'Your day in a line', detail: 'Read this first each morning. Tap Why this reading? any time to see where it comes from.' }
        : { target: '.gauge-btn', title: 'Your day score', detail: '50 is an ordinary day. Tap the ring to see what makes up today.' },
      { target: 'button.listen', title: 'Listen to your day', detail: 'A short audio reading, under two minutes. Good with morning tea.' },
      { target: 'nav.tabbar', title: 'Ask and Calendar', detail: 'Ask about anything in your life. Calendar holds good times and festivals.' },
    ];
    this.shown.set(tips.filter((t) => document.querySelector(t.target)));
    if (!this.shown().length) return this.done();
    this.step.set(0);
    this.place();
  }

  private place(): void {
    const tip = this.shown()[this.step()];
    const el = tip ? document.querySelector<HTMLElement>(tip.target) : null;
    if (!tip || !el) return;
    el.scrollIntoView({ block: 'center' });
    const r = el.getBoundingClientRect();
    this.viewportHeight.set(innerHeight);
    this.spot.set({
      tip,
      top: r.top,
      left: r.left,
      width: r.width,
      height: r.height,
      below: r.bottom + 220 < innerHeight,
    });
  }
}
