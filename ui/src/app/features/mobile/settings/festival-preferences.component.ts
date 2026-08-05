import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FestivalRegion, PreferencesService } from '../../../core/preferences.service';

interface FestivalChoice {
  id: FestivalRegion;
  title: string;
  detail: string;
}

@Component({
  selector: 'as-settings-festivals',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './festival-preferences.component.html',
  styleUrl: './festival-preferences.component.scss',
})
export class FestivalPreferencesComponent {
  protected readonly preferences = inject(PreferencesService);

  protected readonly choices: FestivalChoice[] = [
    { id: 'pan-india', title: 'Pan-India essentials', detail: 'Diwali, Holi, Navaratri, Ekadashi and widely observed festivals.' },
    { id: 'north', title: 'North Indian / Purnimanta', detail: 'North-style lunar month convention and northern observance dates.' },
    { id: 'south', title: 'South Indian / Amanta', detail: 'Telugu, Tamil, Kannada, Malayali, Deccan and Gujarat-style observance families.' },
  ];

  protected selected(id: FestivalRegion): boolean {
    return this.preferences.festivalRegions().includes(id);
  }

  protected toggle(id: FestivalRegion): void {
    const current = this.preferences.festivalRegions();
    const next = current.includes(id) ? current.filter((region) => region !== id) : [...current, id];
    this.preferences.festivalRegions.set(next.length ? next : ['pan-india']);
  }

  protected selectPreset(regions: FestivalRegion[]): void {
    this.preferences.festivalRegions.set([...new Set(regions)]);
  }
}
