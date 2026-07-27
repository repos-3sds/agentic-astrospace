import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';
import { EastChartComponent } from '../chart/east-chart.component';

@Component({
  selector: 'as-first-insight',
  standalone: true,
  imports: [RouterLink, EastChartComponent],
  templateUrl: './first-insight.component.html',
  styleUrl: './first-insight.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'as-mobile' },
})
export class FirstInsightComponent {
  protected readonly preferences = inject(PreferencesService);
  private readonly kundlis = inject(KundliStore);
  protected readonly name = computed(() => this.kundlis.active()?.name ?? '');
  protected readonly guidedLead = computed(() =>
    this.preferences.tone() === 'direct'
      ? 'Your strength is staying deliberate when other people rush.'
      : 'One of your strengths is staying thoughtful when other people rush.',
  );
  protected readonly balancedLead = computed(() =>
    this.preferences.tone() === 'direct'
      ? 'Warm expression meets a careful emotional core.'
      : 'There is warmth in how you express yourself and care in how you process feelings.',
  );
  protected readonly cells = [
    { planets: 'Su·Me', x: 67.6, y: 5.9 },
    { planets: 'As·Ve', x: 41.9, y: 12.6 },
    { planets: 'Mo', x: 86, y: 21.9 },
    { planets: 'Ju', x: 13.2, y: 45.9 },
    { planets: 'Sa', x: 87.9, y: 71.9 },
  ];
}
