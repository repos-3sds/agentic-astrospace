import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { Kundli } from '../../../core/models';

@Component({
  selector: 'as-profile-management',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <header class="profiles-appbar">
      <a routerLink="/m/settings" aria-label="Back"><img src="mobile/back.svg" alt="" /></a>
      <h1>Manage Profiles</h1>
      <a class="text-link" routerLink="/m/settings/profiles/new">Add</a>
    </header>

    <main class="profiles-main">
      @if (loading()) {
        <section class="profiles-state"><b>Loading profiles</b><p>Checking the profiles on this account.</p></section>
      } @else if (error()) {
        <section class="profiles-state error" role="alert">
          <b>Profiles could not load</b>
          <p>{{ error() }}</p>
          <button type="button" (click)="reload()">Retry</button>
        </section>
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
                  <small>{{ profile.relation || 'Profile' }} · {{ birthSummary(profile) }}</small>
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
    return `${profile.birth_day}/${profile.birth_month}/${profile.birth_year}, ${String(profile.birth_hour).padStart(2, '0')}:${String(profile.birth_minute).padStart(2, '0')}`;
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
