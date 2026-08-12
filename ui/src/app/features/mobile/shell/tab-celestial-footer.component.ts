import { ChangeDetectionStrategy, Component, input } from '@angular/core';

export type TabPlanet = 'moon' | 'mercury' | 'earth' | 'saturn' | 'jupiter' | 'venus';

export function tabPlanetForPath(path: string): TabPlanet | null {
  if (path === '/m/today') return 'moon';
  if (path === '/m/ask') return 'mercury';
  if (path === '/m/explore' || path === '/m/chart') return 'earth';
  if (path === '/m/chart/periods') return 'saturn';
  if (path === '/m/calendar') return 'jupiter';
  if (path === '/m/settings') return 'venus';
  return null;
}

@Component({
  selector: 'as-tab-celestial-footer',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './tab-celestial-footer.component.html',
  styleUrl: './tab-celestial-footer.component.scss',
})
export class TabCelestialFooterComponent {
  readonly planet = input.required<TabPlanet>();
}
