import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { Kundli } from '../../../core/models';
import { GenericErrorComponent } from '../states/generic-error.component';
import { BackBarComponent } from '../shared/back-bar.component';
import { profileRelationLabel } from './profile-fields';
import { birthDate } from '../format-date';

@Component({
  selector: 'as-profile-management',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackBarComponent, GenericErrorComponent, RouterLink],
  template: `
    <as-back-bar back="/m/settings" crumb="Settings" title="Profiles">
      <a class="text-link" routerLink="/m/settings/profiles/new">Add</a>
    </as-back-bar>

    <main class="profiles-main">
      @if (loading()) {
        <section class="profiles-state"><b>Loading profiles</b><p>Checking the profiles on this account.</p></section>
      } @else if (error()) {
        <as-generic-error role="alert" [message]="error()!" (retried)="reload()" />
      } @else if (!kundlis.kundlis().length) {
        <section class="profiles-state">
          <b>No profiles yet</b>
          <p>Add a profile to cast a chart and unlock Today, Ask and readings.</p>
          <a routerLink="/m/settings/profiles/new">Add profile</a>
        </section>
      } @else {
        <section class="profiles-list" aria-label="Profiles">
          @for (profile of kundlis.kundlis(); track profile.id) {
            <article class="profile-card" [class.active]="profile.id === kundlis.activeId()">
              <button type="button" class="profile-main" (click)="activate(profile)">
                <span class="avatar">{{ profile.name.slice(0, 1).toUpperCase() }}</span>
                <span>
                  <b>{{ profile.name }}</b>
                  <small>{{ relationLabel(profile.relation) }} · {{ birthSummary(profile) }}</small>
                </span>
                @if (profile.id === kundlis.activeId()) { <em>Active</em> }
              </button>
              <div class="profile-actions">
                <a [routerLink]="['/m','settings','profiles',profile.id,'memory']">Memory</a>
                <a [routerLink]="['/m','settings','profiles',profile.id,'edit']">Edit</a>
                <a class="danger" [routerLink]="['/m','settings','profiles',profile.id,'delete']">Delete</a>
              </div>
            </article>
          }
        </section>
      }
    </main>
  `,
  styleUrl: './profile-management.component.scss',
})
export class ProfileManagementComponent {
  protected readonly relationLabel = profileRelationLabel;
  protected readonly kundlis = inject(KundliStore);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  constructor() {
    void this.load();
  }

  protected reload(): void {
    void this.load();
  }

  protected activate(profile: Kundli): void {
    this.kundlis.setActive(profile.id);
  }

  protected birthSummary(profile: Kundli): string {
    return `${birthDate(profile.birth_day, profile.birth_month, profile.birth_year)}, ${String(profile.birth_hour).padStart(2, '0')}:${String(profile.birth_minute).padStart(2, '0')}`;
  }

  private async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }
}
