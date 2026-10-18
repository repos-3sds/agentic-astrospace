import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { GenericErrorComponent } from '../states/generic-error.component';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { profileRelationLabel } from '../settings/profile-fields';

@Component({
  selector: 'as-compat-hub',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackLinkDirective, GenericErrorComponent, RouterLink],
  template: `
    <a class="mco-back" [asBack]="['/m','family']"><img src="mobile/back.svg" alt="" /><span>Family</span></a>
    <main class="mco-body">
      <header><h1>Compatibility</h1><p>The traditional 36-point match between two charts</p></header>
      <section class="mco-how"><b>HOW THIS WORKS</b><p>Pick someone you have saved. Siddha compares your two birth charts on the eight traditional points of match and shows the score, what helps, and anything worth a closer look.</p></section>
      <a class="mco-primary" [routerLink]="['/m','compat','add']"><span>+</span>Add a person</a>

      @if (loading()) {
        <section class="mco-empty"><div aria-hidden="true">...</div><b>Loading profiles</b><p>Checking who can be compared.</p></section>
      } @else if (error()) {
        <as-generic-error role="alert" [message]="error()!" (retried)="reload()" />
      } @else if (!partners().length) {
        <section class="mco-empty"><div aria-hidden="true">♡</div><b>No checks yet</b><p>Add another profile to compute your first match.</p></section>
      } @else {
        <p class="mco-label">SELECT A PERSON</p>
        @for (profile of partners(); track profile.id) {
          <a class="mco-recent" [routerLink]="['/m','compat','results']" [queryParams]="{ partner: profile.id }">
            <span class="mco-avatar">{{ profile.name.slice(0, 1).toUpperCase() }}</span>
            <span><b>{{ activeName() }} x {{ profile.name }}</b><small>{{ relationLabel(profile.relation) }} · {{ profile.birth_city }}</small></span>
            <img src="mobile/chevron.svg" alt="" />
          </a>
        }
      }
    </main>
  `,
  styleUrl: './compat-hub.component.scss',
})
export class CompatHubComponent {
  protected readonly relationLabel = profileRelationLabel;
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
