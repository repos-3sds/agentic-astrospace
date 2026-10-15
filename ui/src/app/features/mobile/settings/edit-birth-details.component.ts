import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { KundliPayload } from '../../../core/models';
import { ChartComputingComponent } from '../states/chart-computing.component';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { BirthDetailsFormComponent } from '../shared/birth-details-form.component';

@Component({
  selector: 'as-edit-birth-details',
  standalone: true,
  imports: [BackLinkDirective, ChartComputingComponent, BirthDetailsFormComponent],
  templateUrl: './edit-birth-details.component.html',
  styleUrl: './edit-birth-details.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EditBirthDetailsComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly router = inject(Router);

  protected readonly initial = signal<Partial<KundliPayload> | null>(null);
  protected readonly hideSelf = signal(false);
  protected readonly loading = signal(true);
  protected readonly loadError = signal<string | null>(null);
  protected readonly saving = signal(false);
  protected readonly error = signal<string | null>(null);

  constructor() { void this.load(); }

  private async load(): Promise<void> {
    try {
      await this.kundlis.load();
      const profile = this.kundlis.active();
      if (!profile) throw new Error('No active profile to edit.');
      this.initial.set({
        name: profile.name,
        relation: profile.relation,
        birth_year: profile.birth_year,
        birth_month: profile.birth_month,
        birth_day: profile.birth_day,
        birth_hour: profile.birth_hour,
        birth_minute: profile.birth_minute,
        birth_city: profile.birth_city,
        birth_nation: profile.birth_nation,
        birth_time_accuracy: profile.birth_time_accuracy ?? 'exact',
      });
      const self = this.kundlis.kundlis().find((item) => (item.relation ?? '').toLowerCase() === 'self');
      this.hideSelf.set(!!self && self.id !== profile.id);
    } catch (error) {
      this.loadError.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  protected async save(payload: KundliPayload): Promise<void> {
    const profile = this.kundlis.active();
    if (!profile) return;
    this.saving.set(true);
    this.error.set(null);
    try {
      await this.kundlis.update(profile.id, payload);
      await this.router.navigate(['/m', 'settings']);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.saving.set(false);
    }
  }
}
