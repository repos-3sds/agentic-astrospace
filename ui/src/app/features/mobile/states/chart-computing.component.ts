import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'as-chart-computing',
  standalone: true,
  template: `
    <div class="compute-mark" aria-hidden="true"><span></span><i></i></div>
    <h2>Computing your chart</h2>
    <p>Calculating planetary positions, houses, dashas, and current transits…</p>
    <div class="compute-dots" aria-hidden="true"><b></b><b></b><b></b></div>
  `,
  styleUrl: './chart-computing.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { role: 'status', 'aria-live': 'polite' },
})
export class ChartComputingComponent {}
