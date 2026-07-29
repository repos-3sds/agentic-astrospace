import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

/**
 * One house's worth of writing on the chart.
 *
 * Either line may be absent: the small preview labels some houses with only a
 * sign and others with only their occupants, while the full render stacks both.
 *
 * Positions are percentages of the square frame — the same placements then
 * serve the 160px preview and the 337px render, which is the whole reason they
 * are not stored in pixels.
 */
export interface ChartCell {
  sign?: string;
  planets?: string;
  /** Left / top of the text block, as a percentage of the frame. */
  x: number;
  y: number;
}

export interface PlanetSelection {
  cell: ChartCell;
  planet: string;
}

/**
 * East Indian rashi chart (Figma nodes 46:154 preview, 44:96 full).
 *
 * The frame is a 3x3 grid with the four corner cells split diagonally — nine
 * cells, twelve houses, centre empty. That is the East Indian (Bengali and
 * Odia) convention, not the North Indian diamond or the South Indian ring, and
 * the screens say "Eastern" for exactly that reason: the same chart drawn three
 * ways is three different-looking diagrams, and a reader who knows one will not
 * recognise the others.
 *
 * The grid is static structure, so it is the exported SVG used as-is. What sits
 * on it is data — the glyphs move with the chart — so those are positioned
 * rather than baked into the export. Same split as the day gauge's track and
 * arc, and for the same reason.
 *
 * The two frames are separate exports rather than one scaled: their geometry
 * scales exactly but their stroke weights do not (2.4 at 160px, 2.2 at 337px),
 * so rescaling the small one would draw the big chart with a line more than
 * twice as heavy as designed.
 */
@Component({
  selector: 'as-east-chart',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <img
      class="frame"
      [src]="size() === 'full' ? 'mobile/chart-east-lg.svg' : 'mobile/chart-east.svg'"
      alt=""
      aria-hidden="true"
    />
    @for (cell of cells(); track cell.x + '/' + cell.y) {
      @if (interactive() && cell.planets) {
        <span
          class="cell interactive"
          [class.edge-right]="cell.x >= 70"
          [class.edge-bottom]="cell.y >= 80"
          [style.left.%]="cell.x"
          [style.top.%]="cell.y"
        >
          @if (cell.sign) { <span class="sign">{{ cell.sign }}</span> }
          <span class="planet-list">
            @for (planet of planetGlyphs(cell.planets); track planet) {
              <button
                class="planet"
                type="button"
                [attr.aria-label]="planet + (cell.sign ? ' in ' + cell.sign : '')"
                (click)="planetSelected.emit({ cell, planet })"
              >{{ planet }}</button>
            }
          </span>
        </span>
      } @else {
        <span
          class="cell"
          [class.edge-right]="cell.x >= 70"
          [class.edge-bottom]="cell.y >= 80"
          [style.left.%]="cell.x"
          [style.top.%]="cell.y"
        >
          @if (cell.sign) { <span class="sign">{{ cell.sign }}</span> }
          @if (cell.planets) { <span class="planets">{{ cell.planets }}</span> }
        </span>
      }
    }
  `,
  styleUrl: './east-chart.component.scss',
  host: {
    '[class.is-full]': "size() === 'full'",
    role: 'img',
    '[attr.aria-label]': 'label()',
  },
})
export class EastChartComponent {
  readonly cells = input.required<ChartCell[]>();
  readonly size = input<'preview' | 'full'>('preview');
  /** Whether occupied houses are tappable — true only on the full render. */
  readonly interactive = input(false);
  readonly label = input('Rashi chart, East Indian style');

  readonly cellSelected = output<ChartCell>();
  readonly planetSelected = output<PlanetSelection>();

  protected planetGlyphs(planets: string): string[] {
    return planets.split('·').map((planet) => planet.trim()).filter(Boolean);
  }
}
