import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';

@Component({
  selector: 'as-profile-delete',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink],
  template: `
    <header class="profiles-appbar">
      <a routerLink="/m/settings/profiles" aria-label="Back"><img src="mobile/back.svg" alt="" /></a>
      <h1>Delete Profile</h1>
      <span></span>
    </header>

    <main class="profiles-main">
      @if (loading()) {
        <section class="profiles-state"><b>Loading profile</b><p>Checking which profile will be deleted.</p></section>
      } @else if (error()) {
        <section class="profiles-state error" role="alert">
          <b>Profile could not load</b>
          <p>{{ error() }}</p>
        </section>
      } @else if (profile(); as item) {
        <section class="delete-card">
          <div class="danger-mark">!</div>
          <h2>Delete {{ item.name }}?</h2>
          <p>This removes this profile's chart data from the account. Other profiles stay available.</p>
          @if (item.id === kundlis.activeId()) {
            <aside>The active profile will switch to another available profile after deletion.</aside>
          }
          <label>TYPE {{ item.name.toUpperCase() }} TO CONFIRM<input [(ngModel)]="confirmation" autocomplete="off" /></label>
        </section>
      }
    </main>

    <footer class="profiles-footer split">
      <a routerLink="/m/settings/profiles">Cancel</a>
      <button type="button" [disabled]="!canDelete() || deleting()" (click)="remove()">
        {{ deleting() ? 'Deleting...' : 'Delete Profile' }}
      </button>
    </footer>
  `,
  styleUrl: './profile-management.component.scss',
})
export class ProfileDeleteComponent {
  protected readonly kundlis = inject(KundliStore);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly id = this.route.snapshot.paramMap.get('id');

  protected readonly loading = signal(true);
  protected readonly deleting = signal(false);
  protected readonly error = signal<string | null>(null);
  protected confirmation = '';
  protected readonly profile = computed(() => this.kundlis.kundlis().find((item) => item.id === this.id) ?? null);

  constructor() {
    void this.load();
  }

  protected async remove(): Promise<void> {
    if (!this.id || !this.canDelete()) return;
    this.deleting.set(true);
    this.error.set(null);
    try {
      await this.kundlis.remove(this.id);
      await this.router.navigate(['/m', 'settings', 'profiles']);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.deleting.set(false);
    }
  }

  protected canDelete(): boolean {
    const profile = this.profile();
    return !!profile && this.confirmation.trim().toUpperCase() === profile.name.toUpperCase();
  }

  private async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
      if (!this.profile()) throw new Error('Profile not found.');
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }
}
