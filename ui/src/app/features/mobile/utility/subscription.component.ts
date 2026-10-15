import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import {
  EntitlementCatalog,
  EntitlementService,
  EntitlementSnapshot,
} from '../../../core/entitlement.service';
import { GenericErrorComponent } from '../states/generic-error.component';
import { BackBarComponent } from '../shared/back-bar.component';

@Component({
  selector: 'as-subscription',
  standalone: true,
  imports: [BackBarComponent, GenericErrorComponent],
  template: `
    <as-back-bar back="/m/settings" crumb="Settings" title="Plans" />
    <main class="plan-page">
      @if (loading()) {
        <section class="plan-state" aria-live="polite">Checking your access…</section>
      } @else if (error()) {
        <as-generic-error role="alert" message="Plans could not load. Your current access has not changed." (retried)="load()" />
      } @else if (current(); as plan) {
        <section class="plan-summary">
          <span class="plan-kicker">CURRENT PLAN</span>
          <h2>{{ planLabel(plan) }}</h2>
          <p>{{ planSummary(plan) }}</p>
          @if (plan.status === 'grace') {
            <small>Billing grace period active through {{ plan.grace_ends_at || 'the date provided by your store' }}.</small>
          }
        </section>

        <section class="plan-included">
          <h2>Included now</h2>
          <ul>
            @for (item of includedCapabilities(); track item) {
              <li>{{ item }}</li>
            }
          </ul>
        </section>

        <aside>
          Purchases are not available in this build. Prices, trials, renewal,
          cancellation and restore will appear only after store verification is ready.
        </aside>
        <button type="button" disabled>Compare plans</button>
        <p class="restore">No payment or plan change has been made.</p>
      }
    </main>
  `,
  styleUrl: './utility.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SubscriptionComponent implements OnInit {
  private readonly entitlements = inject(EntitlementService);

  protected readonly loading = signal(true);
  protected readonly error = signal(false);
  protected readonly current = signal<EntitlementSnapshot | null>(null);
  private readonly registry = signal<EntitlementCatalog | null>(null);

  ngOnInit(): void {
    void this.load();
  }

  protected async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(false);
    try {
      const [snapshot, catalog] = await Promise.all([
        this.entitlements.snapshot(),
        this.entitlements.catalog(),
      ]);
      this.current.set(snapshot);
      this.registry.set(catalog);
    } catch {
      this.error.set(true);
    } finally {
      this.loading.set(false);
    }
  }

  protected planLabel(plan: EntitlementSnapshot): string {
    const tier = plan.access_tier[0].toUpperCase() + plan.access_tier.slice(1);
    return plan.account_topology === 'family' ? `${tier} Family` : tier;
  }

  protected planSummary(plan: EntitlementSnapshot): string {
    if (plan.access_tier === 'pro') return 'Advanced practitioner workflow is available.';
    if (plan.access_tier === 'plus') return 'Deeper personal guidance and planning are available.';
    return 'Core guidance, safety, sources and profile correctness remain available.';
  }

  protected includedCapabilities(): string[] {
    const snapshot = this.current();
    const catalog = this.registry();
    if (!snapshot || !catalog) return [];
    return Object.entries(catalog.capabilities)
      .filter(([key, definition]) => definition.kind === 'flag' && snapshot.entitlements[key] === true)
      .map(([, definition]) => definition.description);
  }
}
