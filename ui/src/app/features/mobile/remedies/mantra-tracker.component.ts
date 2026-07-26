import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

/**
 * Remedy detail — mantra tracker (Figma node 29:109).
 *
 * The count ring is data, not decoration: it redraws on every tap, so — like
 * the day gauge (13:20) — it is a stroked circle rather than the pasted export.
 * The geometry is lifted from the export so it lines up exactly:
 *
 *   outer radius 110, band 15.4 wide  ->  stroke-width 15.4, centre r 102.3
 *   track #e6dccd (--m-border), arc #b13f2e (--m-accent)
 *
 * The two exported ellipses are the only assets deliberately not used verbatim.
 *
 * On the counting itself: the target is a traditional count (108), and the
 * screen says "traditional practice" in the eyebrow and again above the fold.
 * The streak is there to help someone keep a practice they chose, which is why
 * nothing here warns about breaking it — a lapsed streak is not a consequence,
 * and dressing it as one would turn a practice into a debt.
 */
@Component({
  selector: 'as-mantra-tracker',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './mantra-tracker.component.html',
  styleUrl: './mantra-tracker.component.scss',
})
export class MantraTrackerComponent {
  readonly eyebrow = signal('SATURN DASHA · TRADITIONAL PRACTICE');
  readonly mantra = signal('Om Sham Shanaishcharaya Namah');
  readonly streakDays = signal(6);

  readonly target = signal(108);
  readonly count = signal(45);

  protected readonly streakLabel = computed(
    () => `${this.streakDays()}-day streak — keep it going`,
  );

  // Ring geometry, from the 220px export.
  protected readonly SIZE = 220;
  protected readonly C = 110;
  protected readonly R = 102.3;
  protected readonly STROKE = 15.4;
  protected readonly CIRCUMFERENCE = 2 * Math.PI * 102.3;

  protected readonly dashOffset = computed(() => {
    const target = this.target();
    const fraction = target > 0 ? this.count() / target : 0;
    return this.CIRCUMFERENCE * (1 - Math.min(1, Math.max(0, fraction)));
  });

  /** Counts up to the target and stops. Past 108 the count means nothing. */
  protected tap(): void {
    this.count.update((n) => Math.min(this.target(), n + 1));
  }

  protected readonly done = computed(() => this.count() >= this.target());
}
