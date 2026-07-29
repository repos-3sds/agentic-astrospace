import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';

@Component({
  selector: 'as-compat-hub',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <a class="mco-back" [routerLink]="['/m','chart']"><img src="mobile/back.svg" alt="" /><span>Your Chart</span></a>
    <main class="mco-body">
      <header><h1>Compatibility</h1><p>Ashta Koota matching - 36 points, computed honestly</p></header>
      <section class="mco-how"><b>HOW THIS WORKS</b><p>We compare two saved birth profiles across the 8 classical kootas, flag doshas honestly, and show the computed base layer before any interpretation.</p></section>
      <a class="mco-primary" [routerLink]="['/m','compat','add']"><span>+</span>Add a person</a>

      @if (loading()) {
        <section class="mco-empty"><div aria-hidden="true">...</div><b>Loading profiles</b><p>Checking who can be compared.</p></section>
      } @else if (error()) {
        <section class="mco-empty error" role="alert"><div aria-hidden="true">!</div><b>Profiles could not load</b><p>{{ error() }}</p><button type="button" (click)="reload()">Retry</button></section>
      } @else if (!partners().length) {
        <section class="mco-empty"><div aria-hidden="true">♡</div><b>No checks yet</b><p>Add another profile to compute your first match.</p></section>
      } @else {
        <p class="mco-label">SELECT A PERSON</p>
        @for (profile of partners(); track profile.id) {
          <a class="mco-recent" [routerLink]="['/m','compat','results']" [queryParams]="{ partner: profile.id }">
            <span class="mco-avatar">{{ profile.name.slice(0, 1).toUpperCase() }}</span>
            <span><b>{{ activeName() }} x {{ profile.name }}</b><small>{{ profile.relation || 'Profile' }} · {{ profile.birth_city }}</small></span>
            <img src="mobile/chevron.svg" alt="" />
          </a>
        }
      }
    </main>
  `,
  styleUrl: './compat-hub.component.scss',
})
export class CompatHubComponent {
  private readonly kundlis = inject(KundliStore);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly partners = computed(() =>
    this.kundlis.kundlis().filter((profile) => profile.id !== this.kundlis.activeId()),
  );
  protected readonly activeName = computed(() => this.kundlis.active()?.name ?? 'You');

  constructor() {
    void this.load();
  }

  protected reload(): void {
    void this.load();
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
