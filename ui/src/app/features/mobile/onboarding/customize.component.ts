import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DefaultChartStyle, PreferencesService } from '../../../core/preferences.service';

interface ChartStyleChoice {
  id: DefaultChartStyle;
  label: string;
  description: string;
}

/**
 * Customize (new — not a Figma-tracked node; see mobile_screen_build_plan.md)
 * — chart-view preference between Persona and Birth Details.
 *
 * This stays deliberately light. Regional festival preferences are handled in
 * Settings where the user has more context and more room.
 */
@Component({
  selector: 'as-customize',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './customize.component.html',
  styleUrl: './customize.component.scss',
  host: { class: 'as-mobile' },
})
export class CustomizeComponent {
  protected readonly preferences = inject(PreferencesService);

  protected readonly chartStyles: ChartStyleChoice[] = [
    { id: 'south', label: 'South Indian', description: 'Fixed-sign square layout' },
    { id: 'north', label: 'North Indian', description: 'Diamond house layout' },
    { id: 'eastern', label: 'Eastern', description: 'Bengal/Odisha grid layout' },
  ];

  protected chooseChartStyle(id: DefaultChartStyle): void {
    this.preferences.chartStyle.set(id);
  }
}
