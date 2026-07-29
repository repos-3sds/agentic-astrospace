import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { Kundli, KundliPayload } from '../../../core/models';
import { ChartComputingComponent } from '../states/chart-computing.component';

@Component({
  selector: 'as-profile-form',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink, ChartComputingComponent],
  template: `
    <header class="profiles-appbar">
      <a routerLink="/m/settings/profiles" aria-label="Back"><img src="mobile/back.svg" alt="" /></a>
      <h1>{{ editingId() ? 'Edit Profile' : 'Add Profile' }}</h1>
      <span></span>
    </header>

    <main class="profiles-main">
      <aside class="profiles-note">
        Birth details recalculate the chart for this profile only. Other profiles keep their own data.
      </aside>

      @if (loading()) {
        <section class="profiles-state"><b>Loading profile</b><p>Preparing the profile form.</p></section>
      } @else {
        <form id="profile-form" class="profile-form" (ngSubmit)="save()">
          <label>NAME<input name="name" [(ngModel)]="name" autocomplete="name" /></label>
          <label>RELATION<input name="relation" [(ngModel)]="relation" placeholder="self, partner, child" /></label>
          <label>DATE OF BIRTH<input name="date" [(ngModel)]="date" type="date" /></label>
          <label>TIME OF BIRTH<input name="time" [(ngModel)]="time" type="time" /></label>
          <label>PLACE OF BIRTH<input name="city" [(ngModel)]="city" autocomplete="address-level2" /></label>
          <label>COUNTRY CODE<input name="nation" [(ngModel)]="nation" maxlength="2" autocomplete="country" /></label>
          @if (error()) { <p class="profiles-error" role="alert">{{ error() }}</p> }
        </form>
      }
    </main>

    <footer class="profiles-footer">
      <button type="submit" form="profile-form" [disabled]="loading() || saving()">
        {{ saving() ? 'Saving...' : editingId() ? 'Save Changes' : 'Add Profile' }}
      </button>
    </footer>

    @if (saving()) { <as-chart-computing /> }
  `,
  styleUrl: './profile-management.component.scss',
})
export class ProfileFormComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly editingId = signal<string | null>(this.route.snapshot.paramMap.get('id'));

  protected name = '';
  protected relation = 'self';
  protected date = '';
  protected time = '';
  protected city = '';
  protected nation = 'IN';

  constructor() {
    void this.load();
  }

  protected async save(): Promise<void> {
    const payload = this.payload();
    if (!payload) return;
    this.saving.set(true);
    this.error.set(null);
    try {
      const id = this.editingId();
      if (id) {
        await this.kundlis.update(id, payload);
        this.kundlis.setActive(id);
      } else {
        await this.kundlis.create(payload);
      }
      await this.router.navigate(['/m', 'settings', 'profiles']);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.saving.set(false);
    }
  }

  private async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
      const id = this.editingId();
      if (id) {
        const profile = this.kundlis.kundlis().find((item) => item.id === id);
        if (!profile) throw new Error('Profile not found.');
        this.applyProfile(profile);
      }
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  private applyProfile(profile: Kundli): void {
    this.name = profile.name;
    this.relation = profile.relation || 'self';
    this.date = `${profile.birth_year}-${String(profile.birth_month).padStart(2, '0')}-${String(profile.birth_day).padStart(2, '0')}`;
    this.time = `${String(profile.birth_hour).padStart(2, '0')}:${String(profile.birth_minute).padStart(2, '0')}`;
    this.city = profile.birth_city;
    this.nation = profile.birth_nation || 'IN';
  }

  private payload(): KundliPayload | null {
    const [year, month, day] = this.date.split('-').map(Number);
    const [hour, minute] = this.time.split(':').map(Number);
    if (!this.name.trim() || !year || !month || !day || Number.isNaN(hour) || Number.isNaN(minute) || !this.city.trim()) {
      this.error.set('Complete each birth detail before saving.');
      return null;
    }
    return {
      name: this.name.trim(),
      relation: this.relation.trim() || 'self',
      birth_year: year,
      birth_month: month,
      birth_day: day,
      birth_hour: hour,
      birth_minute: minute,
      birth_city: this.city.trim(),
      birth_nation: (this.nation.trim() || 'IN').toUpperCase(),
    };
  }
}
