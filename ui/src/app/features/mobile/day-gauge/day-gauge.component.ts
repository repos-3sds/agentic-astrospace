import { ChangeDetectionStrategy, Component, computed, input, effect, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';

/**
 * [band, from, to] on the 0-100 dial, matching DAY_BANDS in
 * astrospace/context/daily.py (Go gently, Mixed, Steady, Good).
 */
export const DAY_BANDS: [string, number, number][] = [
  ['tough', 0, 30],
  ['mixed', 30, 50],
  ['steady', 50, 70],
  ['good', 70, 100],
];

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
 *
 * Band marks (2026-10-28): testers could not tell what a "26" meant, so the
 * ring carries hairline gaps at 30, 50 and 70 and its unfilled part is tinted
 * by band. The ring itself is unchanged; tapping it lists what each band means.
 */
@Component({
  selector: 'as-day-gauge',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DecimalPipe],
  template: `
    <svg [attr.viewBox]="'0 0 ' + SIZE + ' ' + SIZE" [attr.width]="SIZE" [attr.height]="SIZE"
         role="img" [attr.aria-label]="label() + ', ' + score() + ' out of 100'">
      @for (seg of SEGMENTS; track seg.band) {
        <circle class="track" [attr.data-seg]="seg.band" [attr.cx]="C" [attr.cy]="C" [attr.r]="R"
                [attr.stroke-width]="STROKE" fill="none"
                [attr.stroke-dasharray]="seg.dash" [attr.stroke-dashoffset]="seg.offset"
                [attr.transform]="'rotate(-90 ' + C + ' ' + C + ')'" />
      }
      @for (seg of arcs(); track $index) {
        <circle class="arc" [attr.cx]="C" [attr.cy]="C" [attr.r]="R"
                [attr.stroke-width]="STROKE" fill="none" stroke-linecap="butt"
                [attr.stroke-dasharray]="seg.dash" [attr.stroke-dashoffset]="seg.offset"
                [attr.transform]="'rotate(-90 ' + C + ' ' + C + ')'" />
      }
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

  /**
   * The unfilled ring is tinted by band (Go gently 0-29, Mixed 30-49, Steady
   * 50-69, Good 70-100), with a hairline gap at each boundary, so the reader
   * can see which band the score sits in and how near the next one it is.
   */
  private readonly GAP = 1.6;

  protected readonly SEGMENTS = DAY_BANDS.map(([band, from, to]) => {
    const len = ((to - from) / 100) * this.CIRCUMFERENCE - this.GAP;
    return { band, dash: `${len} ${this.CIRCUMFERENCE}`, offset: -((from / 100) * this.CIRCUMFERENCE + this.GAP / 2) };
  });

  protected readonly animatedScore = signal(0);

  constructor() {
    effect(() => {
      const target = this.score();
      // Add a slight delay to allow the gauge to render at 0 before animating to the target
      setTimeout(() => this.animatedScore.set(target), 50);
    });
  }

  /** The filled arc, broken at the same band gaps as the track. */
  protected readonly arcs = computed(() => {
    const value = Math.min(100, Math.max(0, this.animatedScore()));
    const gap = this.GAP;
    return DAY_BANDS.filter(([, from]) => value > from).map(([, from, to]) => {
      const end = Math.min(value, to);
      const len = Math.max(0, ((end - from) / 100) * this.CIRCUMFERENCE - (end === to ? gap : gap / 2));
      return { dash: `${len} ${this.CIRCUMFERENCE}`, offset: -((from / 100) * this.CIRCUMFERENCE + gap / 2) };
    });
  });

}
