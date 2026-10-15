import { Location } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { AnalyticsService } from '../../../core/analytics.service';
import { NavigationHistoryService } from '../../../core/navigation-history.service';
import { Kundli, KundliPayload } from '../../../core/models';
import { ChartComputingComponent } from '../states/chart-computing.component';
import { BirthDetailsFormComponent } from '../shared/birth-details-form.component';
import { BackBarComponent } from '../shared/back-bar.component';
import { LockedStateComponent } from '../shared/locked-state.component';
import { EntitlementDenial, EntitlementLimitError } from '../../../core/entitlement-denial';

@Component({
  selector: 'as-profile-form',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackBarComponent, LockedStateComponent, ChartComputingComponent, BirthDetailsFormComponent],
  template: `
    <as-back-bar back="/m/settings/profiles" crumb="Profiles" [title]="editingId() ? 'Edit profile' : 'Add a profile'" />

    <main class="profiles-main">
      <aside class="profiles-note">
        Birth details recalculate the chart for this profile only. Other profiles keep their own data.
      </aside>

      @if (loading()) {
        <section class="profiles-state"><b>Loading profile</b><p>Preparing the profile form.</p></section>
      } @else if (loadError(); as message) {
        <section class="profiles-state error"><b>Profile not found</b><p>{{ message }}</p></section>
      } @else if (limitDenial(); as denial) {
        <as-locked-state [denial]="denial" />
      } @else {
        <as-birth-details-form
          [initial]="initial()"
          [hideSelf]="hideSelf()"
          [submitLabel]="editingId() ? 'Save changes' : 'Add profile'"
          busyLabel="Saving…"
          [saving]="saving()"
          [error]="error()"
          (submitted)="save($event)"
        />
      }
    </main>

    @if (saving()) { <as-chart-computing /> }
  `,
  styleUrl: './profile-management.component.scss',
})
export class ProfileFormComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly location = inject(Location);
  private readonly history = inject(NavigationHistoryService);
  private readonly analytics = inject(AnalyticsService);

  protected readonly loading = signal(true);
  protected readonly loadError = signal<string | null>(null);
  protected readonly saving = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly limitDenial = signal<EntitlementDenial | null>(null);
  protected readonly editingId = signal<string | null>(this.route.snapshot.paramMap.get('id'));
  protected readonly initial = signal<Partial<KundliPayload> | null>(null);
  /** "Myself" is offered only while the account has no self profile, or when editing it. */
  protected readonly hideSelf = signal(false);

  constructor() {
    void this.load();
  }

  protected async save(payload: KundliPayload): Promise<void> {
    this.saving.set(true);
    this.error.set(null);
    try {
      const id = this.editingId();
      if (id) {
        await this.kundlis.update(id, payload);
      } else {
        await this.kundlis.create(payload, { activate: false });
        this.analytics.track('profile_added', { relation: payload.relation });
      }
      // Back to wherever the form was opened from (Family or Settings ›
      // Profiles), so saving does not drop the reader on a different tab.
      if (this.history.canGoBack()) this.location.back();
      else await this.router.navigate(['/m', 'settings', 'profiles']);
    } catch (error) {
      if (error instanceof EntitlementLimitError) this.limitDenial.set(error.denial);
      else this.error.set((error as Error).message);
    } finally {
      this.saving.set(false);
    }
  }

  private async load(): Promise<void> {
    this.loading.set(true);
    this.loadError.set(null);
    try {
      await this.kundlis.load();
      const id = this.editingId();
      const self = this.kundlis.kundlis().find((item) => (item.relation ?? '').toLowerCase() === 'self');
      if (id) {
        const profile = this.kundlis.kundlis().find((item) => item.id === id);
        if (!profile) throw new Error('Profile not found.');
        this.initial.set(fromProfile(profile));
        this.hideSelf.set(!!self && self.id !== id);
      } else {
        // A second profile is someone else; the backend refuses a second
        // self and the form should not offer it.
        this.initial.set({ relation: self ? 'friend' : 'self' });
        this.hideSelf.set(!!self);
      }
    } catch (error) {
      this.loadError.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }
}

function fromProfile(profile: Kundli): Partial<KundliPayload> {
  return {
    name: profile.name,
    relation: profile.relation,
    birth_year: profile.birth_year,
    birth_month: profile.birth_month,
    birth_day: profile.birth_day,
    birth_hour: profile.birth_hour,
    birth_minute: profile.birth_minute,
    birth_city: profile.birth_city,
    birth_nation: profile.birth_nation || 'IN',
    birth_time_accuracy: profile.birth_time_accuracy ?? 'exact',
  };
}
