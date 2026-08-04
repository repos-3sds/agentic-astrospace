import { ChangeDetectionStrategy, Component, computed, input, effect, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';

/**
 * Day-quality gauge (Figma node 13:20).
 *
 * Figma exported this as two flat SVGs — a track and a 72%-filled arc. The arc
 * is data, not decoration: it has to redraw for every score, so it is rendered
 * as a stroked circle rather than pasted as a static asset. The geometry is
 * taken from the export so it lines up exactly:
 *
 *   outer radius 52, ring inset 11.44  ->  stroke-width 11.44, centre r 46.28
 *   track #e6dccd, arc #2f7d57 (--as-good)
 *
 * This is the one place the exported asset is deliberately not used verbatim.
 */
@Component({
  selector: 'as-day-gauge',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DecimalPipe],
  template: `
    <svg [attr.viewBox]="'0 0 ' + SIZE + ' ' + SIZE" [attr.width]="SIZE" [attr.height]="SIZE"
         role="img" [attr.aria-label]="label() + ', ' + score() + ' out of 100'">
      <circle class="track" [attr.cx]="C" [attr.cy]="C" [attr.r]="R"
              [attr.stroke-width]="STROKE" fill="none" />
      <circle class="arc" [attr.cx]="C" [attr.cy]="C" [attr.r]="R"
              [attr.stroke-width]="STROKE" fill="none" stroke-linecap="butt"
              [attr.stroke-dasharray]="CIRCUMFERENCE"
              [attr.stroke-dashoffset]="dashOffset()"
              [attr.transform]="'rotate(-90 ' + C + ' ' + C + ')'" />
    </svg>
    <div class="readout" aria-hidden="true">
      <span class="score">{{ animatedScore() | number:'1.0-0' }}</span>
      <span class="label">{{ label() }}</span>
    </div>
  `,
  styleUrl: './day-gauge.component.scss',
})
export class DayGaugeComponent {
  readonly score = input.required<number>();
  readonly label = input.required<string>();

  protected readonly SIZE = 104;
  protected readonly C = 52;
  protected readonly R = 46.28;
  protected readonly STROKE = 11.44;
  protected readonly CIRCUMFERENCE = 2 * Math.PI * 46.28;

  protected readonly animatedScore = signal(0);

  constructor() {
    effect(() => {
      const target = this.score();
      // Add a slight delay to allow the gauge to render at 0 before animating to the target
      setTimeout(() => this.animatedScore.set(target), 50);
    });
  }

  protected readonly dashOffset = computed(() => {
    const clamped = Math.min(100, Math.max(0, this.animatedScore()));
    return this.CIRCUMFERENCE * (1 - clamped / 100);
  });
}
