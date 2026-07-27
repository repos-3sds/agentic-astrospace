import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { ChartCell } from './east-chart.component';

@Component({
  selector: 'as-regional-chart',
  standalone: true,
  template: `
    @if (chartStyle() === 'South') {
      <div class="south" role="img" aria-label="South Indian birth chart">
        @for (cell of southCells(); track cell.sign) {
          <button type="button" [class.occupied]="cell.planets" (click)="select(cell)">
            <span>{{ cell.sign }}</span><strong>{{ cell.planets }}</strong>
          </button>
        }
        <div class="south-centre"><strong>D1</strong><span>Rāśi</span></div>
      </div>
    } @else {
      <div class="north" role="img" aria-label="North Indian birth chart">
        <img src="mobile/chart-north-grid.svg" alt="" aria-hidden="true" />
        @for (cell of cells(); track cell.sign) {
          <button
            type="button"
            [class.occupied]="cell.planets"
            [style.left.%]="cell.x"
            [style.top.%]="cell.y"
            (click)="select(cell)"
          ><span>{{ cell.sign }}</span><strong>{{ cell.planets }}</strong></button>
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
  readonly cellSelected = output<ChartCell>();

  protected southCells(): ChartCell[] {
    const order = ['Pi', 'Ar', 'Ta', 'Ge', 'Aq', 'Cn', 'Cp', 'Le', 'Sg', 'Sc', 'Li', 'Vi'];
    return order.map((sign) => this.cells().find((cell) => cell.sign === sign) ?? { sign, x: 0, y: 0 });
  }

  protected select(cell: ChartCell): void {
    if (cell.planets) this.cellSelected.emit(cell);
  }
}
