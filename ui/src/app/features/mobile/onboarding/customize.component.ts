import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DefaultChartStyle, PreferencesService } from '../../../core/preferences.service';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { SelectHapticDirective } from '../shared/select-haptic.directive';
import { CityPickerComponent } from '../shared/city-picker.component';
import { PanchangaCity } from '../../../core/models';

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
  imports: [BackLinkDirective, CityPickerComponent, RouterLink, SelectHapticDirective],
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

  /**
   * Where the reader lives now. Without it, timings fall back to the birth
   * city (or the phone's zone), which is how a tester in another country got
   * night-time muhurtas.
   */
  protected chooseHome(city: PanchangaCity): void {
    this.preferences.setPanchangaPlace(city);
    this.preferences.timezoneMode.set('panchanga_place');
  }
}
