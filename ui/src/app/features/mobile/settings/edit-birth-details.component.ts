import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { PanchangaCity } from '../../../core/models';
import { ChartComputingComponent } from '../states/chart-computing.component';
import { BirthPlaceFieldComponent } from './birth-place-field.component';
import { normalizeProfileRelationship, PROFILE_RELATIONSHIPS } from './profile-fields';

@Component({
  selector: 'as-edit-birth-details',
  standalone: true,
  imports: [FormsModule, RouterLink, ChartComputingComponent, BirthPlaceFieldComponent],
  templateUrl: './edit-birth-details.component.html',
  styleUrl: './edit-birth-details.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EditBirthDetailsComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly router = inject(Router);

  protected name = '';
  protected date = '';
  protected time = '';
  protected city = '';
  protected nation = '';
  protected relation = 'self';
  protected readonly relationships = PROFILE_RELATIONSHIPS;
  protected readonly initialPlace = signal<Pick<PanchangaCity, 'city' | 'nation'> | null>(null);
  private placeSelectionRequired = false;
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly error = signal<string | null>(null);

  constructor() { void this.load(); }

  private async load(): Promise<void> {
    try {
      await this.kundlis.load();
      const profile = this.kundlis.active();
      if (!profile) throw new Error('No active profile to edit.');
      this.name = profile.name;
      this.date = `${profile.birth_year}-${String(profile.birth_month).padStart(2, '0')}-${String(profile.birth_day).padStart(2, '0')}`;
      this.time = `${String(profile.birth_hour).padStart(2, '0')}:${String(profile.birth_minute).padStart(2, '0')}`;
      this.city = profile.birth_city;
      this.nation = profile.birth_nation;
      this.relation = normalizeProfileRelationship(profile.relation);
      this.initialPlace.set({ city: this.city, nation: this.nation });
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  protected async save(): Promise<void> {
    const profile = this.kundlis.active();
    const [year, month, day] = this.date.split('-').map(Number);
    const [hour, minute] = this.time.split(':').map(Number);
    if (!profile || !this.name.trim() || !year || !month || !day || Number.isNaN(hour) || Number.isNaN(minute) || !this.city.trim() || this.placeSelectionRequired) {
      this.error.set(this.placeSelectionRequired ? 'Choose the birth place from the search results.' : 'Complete each birth detail before saving.');
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    try {
      await this.kundlis.update(profile.id, {
        name: this.name.trim(), birth_year: year, birth_month: month, birth_day: day,
        birth_hour: hour, birth_minute: minute, birth_city: this.city.trim(),
        birth_nation: this.nation.trim() || profile.birth_nation, relation: this.relation,
      });
      await this.router.navigate(['/m', 'settings']);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.saving.set(false);
    }
  }

  protected onPlaceChange(place: PanchangaCity | null): void {
    this.placeSelectionRequired = !place;
    if (place) {
      this.city = place.city;
      this.nation = place.nation;
    }
  }
}
