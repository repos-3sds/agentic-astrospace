import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { ChartCell, PlanetSelection } from './east-chart.component';

@Component({
  selector: 'as-regional-chart',
  standalone: true,
  template: `
    @if (chartStyle() === 'South') {
      <div class="south" role="img" aria-label="South Indian birth chart">
        @for (cell of southCells(); track cell.sign) {
          <div class="regional-cell" [class.occupied]="cell.planets">
            <span>{{ cell.sign }}</span>
            @if (cell.planets) {
              <strong>
                @for (planet of planetGlyphs(cell.planets); track planet) {
                  <button type="button" (click)="select(cell, planet)">{{ planet }}</button>
                }
              </strong>
            }
          </div>
        }
        <div class="south-centre"><strong>D1</strong><span>Rāśi</span></div>
      </div>
    } @else {
      <div class="north" role="img" aria-label="North Indian birth chart">
        <img src="mobile/chart-north-grid.svg" alt="" aria-hidden="true" />
        @for (cell of cells(); track cell.sign) {
          <div
            class="regional-cell"
            [class.occupied]="cell.planets"
            [style.left.%]="cell.x"
            [style.top.%]="cell.y"
          ><span>{{ cell.sign }}</span>
            @if (cell.planets) {
              <strong>
                @for (planet of planetGlyphs(cell.planets); track planet) {
                  <button type="button" (click)="select(cell, planet)">{{ planet }}</button>
                }
              </strong>
            }
          </div>
        }
      </div>
    }
  `,
  styleUrl: './regional-chart.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RegionalChartComponent {
  readonly chartStyle = input.required<'South' | 'North'>();
  readonly cells = input.required<ChartCell[]>();
  readonly planetSelected = output<PlanetSelection>();

  protected southCells(): ChartCell[] {
    const order = ['Pi', 'Ar', 'Ta', 'Ge', 'Aq', 'Cn', 'Cp', 'Le', 'Sg', 'Sc', 'Li', 'Vi'];
    return order.map((sign) => this.cells().find((cell) => cell.sign === sign) ?? { sign, x: 0, y: 0 });
  }

  protected planetGlyphs(planets: string): string[] {
    return planets.split('·').map((planet) => planet.trim()).filter(Boolean);
  }

  protected select(cell: ChartCell, planet: string): void {
    this.planetSelected.emit({ cell, planet });
  }
}
