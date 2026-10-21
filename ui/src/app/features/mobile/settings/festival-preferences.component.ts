import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { FestivalRegion, PreferencesService } from '../../../core/preferences.service';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { SelectHapticDirective } from '../shared/select-haptic.directive';

interface FestivalChoice {
  id: FestivalRegion;
  title: string;
  detail: string;
}

/**
 * Settings — Festivals to show. A multi-select, so every row is a square
 * tick box (U30). The preset chips that repeated the same choice above the
 * cards are gone: two controls for one setting left readers unsure which
 * one counted.
 */
@Component({
  selector: 'as-settings-festivals',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackLinkDirective, SelectHapticDirective],
  templateUrl: './festival-preferences.component.html',
  styleUrl: './festival-preferences.component.scss',
})
export class FestivalPreferencesComponent {
  protected readonly preferences = inject(PreferencesService);

  protected readonly choices: FestivalChoice[] = [
    { id: 'pan-india', title: 'All-India festivals', detail: 'Diwali, Holi, Navaratri, Ekadashi and others kept across India.' },
    { id: 'north', title: 'North Indian', detail: 'Months end on the full moon (Purnimanta), with northern festival dates.' },
    { id: 'south', title: 'South Indian', detail: 'Months end on the new moon (Amanta). Telugu, Tamil, Kannada, Malayali, Marathi and Gujarati homes.' },
  ];

  protected selected(id: FestivalRegion): boolean {
    return this.preferences.festivalRegions().includes(id);
  }

  protected toggle(id: FestivalRegion): void {
    const current = this.preferences.festivalRegions();
    const next = current.includes(id) ? current.filter((region) => region !== id) : [...current, id];
    this.preferences.festivalRegions.set(next.length ? next : ['pan-india']);
  }
}
