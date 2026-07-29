import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';

@Component({
  selector: 'as-add-prospect',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink],
  template: `
    <a class="mcof-back" [routerLink]="['/m','compat']"><img src="mobile/back.svg" alt="" /><span>Compatibility</span></a>
    <form class="mcof-form" (ngSubmit)="submit()">
      <header><h1>Add the person</h1><p>Create a saved profile, then compute the match from real chart data.</p></header>
      <label>NAME<span><img src="mobile/field-who.svg" alt="" /><input name="name" [(ngModel)]="name" autocomplete="name" /></span></label>
      <label>DATE OF BIRTH<span><img src="mobile/field-date.svg" alt="" /><input name="date" [(ngModel)]="date" type="date" /></span></label>
      <label>TIME OF BIRTH<span><img src="mobile/field-time.svg" alt="" /><input name="time" [(ngModel)]="time" type="time" /></span></label>
      <p class="mcof-approx">Do not know the exact time? <button type="button" (click)="toggleApproximate()">{{ approximate() ? 'Use exact' : 'Mark approximate' }}</button></p>
      <label>PLACE OF BIRTH<span><img src="mobile/pin-accent.svg" alt="" /><input name="place" [(ngModel)]="city" autocomplete="address-level2" /></span></label>
      <label>COUNTRY CODE<span><img src="mobile/pin-accent.svg" alt="" /><input name="nation" [(ngModel)]="nation" maxlength="2" autocomplete="country" /></span></label>
      @if (error()) { <p class="mcof-error" role="alert">{{ error() }}</p> }
      <button class="mcof-submit" type="submit" [disabled]="saving()">{{ saving() ? 'Saving...' : 'Check compatibility' }}</button>
    </form>
  `,
  styleUrl: './add-prospect.component.scss',
})
export class AddProspectComponent {
  private readonly router = inject(Router);
  private readonly kundlis = inject(KundliStore);

  protected readonly approximate = signal(false);
  protected readonly saving = signal(false);
  protected readonly error = signal<string | null>(null);
  protected name = '';
  protected date = '';
  protected time = '';
  protected city = '';
  protected nation = 'IN';

  protected toggleApproximate(): void {
    this.approximate.update((value) => !value);
  }

  protected async submit(): Promise<void> {
    const [year, month, day] = this.date.split('-').map(Number);
    const [hour, minute] = this.time.split(':').map(Number);
    if (!this.name.trim() || !year || !month || !day || Number.isNaN(hour) || Number.isNaN(minute) || !this.city.trim()) {
      this.error.set('Complete each birth detail before checking compatibility.');
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
      const previousActive = this.kundlis.activeId();
      if (!previousActive) {
        this.error.set('Select your own profile before checking compatibility.');
        return;
      }
      const created = await this.kundlis.create({
        name: this.name.trim(),
        relation: 'prospect',
        birth_year: year,
        birth_month: month,
        birth_day: day,
        birth_hour: hour,
        birth_minute: minute,
        birth_city: this.city.trim(),
        birth_nation: (this.nation.trim() || 'IN').toUpperCase(),
        notes: this.approximate() ? 'Birth time is approximate.' : undefined,
      });
      if (previousActive) this.kundlis.setActive(previousActive);
      await this.router.navigate(['/m', 'compat', 'results'], { queryParams: { partner: created.id } });
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.saving.set(false);
    }
  }
}
