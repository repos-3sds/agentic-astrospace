import { ChangeDetectionStrategy, Component, ElementRef, OnInit, computed, inject, signal, viewChild } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Browser } from '@capacitor/browser';
import { Capacitor } from '@capacitor/core';

import { EntitlementService, EntitlementSnapshot, StoreProduct } from '../../../core/entitlement.service';
import { KundliStore } from '../../../core/kundli.store';
import { openLegal } from '../../../core/legal';
import { PurchaseService } from '../../../core/purchase.service';
import { AnalyticsService } from '../../../core/analytics.service';
import { BackBarComponent } from '../shared/back-bar.component';
import { GenericErrorComponent } from '../states/generic-error.component';

interface CompareRow {
  label: string;
  free: string | boolean;
  plus: string | boolean;
  practitioner: string | boolean;
}

type PlanFamily = 'plus' | 'pro';

/**
 * Plans (D2 hybrid pricing): what the reader has, what Plus adds, and
 * question packs for a few more answers without a subscription.
 *
 * Guardrails from the monetisation plan are written into the screen, not
 * left to copy review: nothing here sells relief from a dosha or a reading,
 * doshas and their cancellations are listed as always free, and a refused
 * or failed answer is stated never to use a question.
 *
 * Prices come from the store once it answers (the reader is charged the
 * store's price, in their currency); the server's launch prices in rupees
 * fill in until then.
 */
@Component({
  selector: 'as-subscription',
  standalone: true,
  imports: [BackBarComponent, GenericErrorComponent],
  templateUrl: './subscription.component.html',
  styleUrl: './subscription.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SubscriptionComponent implements OnInit {
  private readonly entitlements = inject(EntitlementService);
  private readonly kundlis = inject(KundliStore);
  private readonly route = inject(ActivatedRoute);
  protected readonly store = inject(PurchaseService);
  private readonly analytics = inject(AnalyticsService);

  private readonly packsSection = viewChild<ElementRef<HTMLElement>>('packsAnchor');

  protected readonly loading = signal(true);
  protected readonly error = signal(false);
  protected readonly current = signal<EntitlementSnapshot | null>(null);
  protected readonly products = signal<StoreProduct[]>([]);
  /** Which paid plan the picker shows; Practitioner is sold as the "pro" tier. */
  protected readonly family = signal<PlanFamily>(
    this.route.snapshot.queryParamMap.get('plan') === 'practitioner' ? 'pro' : 'plus');
  protected readonly selectedPlan = signal(
    this.family() === 'pro' ? 'siddha_practitioner_monthly' : 'siddha_plus_monthly');
  protected readonly busy = signal<string | null>(null);
  protected readonly notice = signal<{ tone: 'good' | 'info' | 'bad'; text: string } | null>(null);

  // Monthly only since 2026-10-19; a yearly plan, if one returns, sorts first.
  protected readonly plans = computed(() =>
    this.products()
      .filter((p) => p.kind === 'plan' && (p.tier ?? 'plus') === this.family())
      .sort((a, b) => (b.months ?? 0) - (a.months ?? 0)));
  protected readonly familyName = computed(() => this.family() === 'pro' ? 'Practitioner' : 'Plus');
  /** Plus readers can still move up to Practitioner; Practitioner has nothing above it. */
  protected readonly canUpgrade = computed(() => (this.current()?.access_tier ?? 'free') !== 'pro');
  protected readonly enforced = computed(() => !!this.current()?.quotas_enforced);
  protected readonly packs = computed(() => this.products().filter((p) => p.kind === 'question_pack'));
  protected readonly isPaid = computed(() => (this.current()?.access_tier ?? 'free') !== 'free');
  /** Paid through Google Play or the App Store, so the store's page can manage it. */
  protected readonly storeManaged = computed(() => this.isPaid() && this.current()?.source === 'revenuecat');

  protected chooseFamily(family: PlanFamily): void {
    this.family.set(family);
    this.selectedPlan.set(family === 'pro' ? 'siddha_practitioner_monthly' : 'siddha_plus_monthly');
  }

  protected readonly usageRows = computed(() => {
    const snapshot = this.current();
    if (!snapshot) return [];
    const ask = this.entitlements.askAllowance();
    const profileLimit = snapshot.entitlements['profiles.max'];
    const rows: { label: string; value: string }[] = [];
    if (ask && ask.limit > 0) rows.push({ label: 'Answers this month', value: `${ask.used} of ${ask.limit}` });
    if (typeof profileLimit === 'number') {
      const held = this.kundlis.kundlis().length;
      // Profiles made before limits existed are kept; only adding is limited.
      rows.push({
        label: 'Profiles',
        value: held > profileLimit ? `${held} · ${profileLimit} included` : `${held} of ${profileLimit}`,
      });
    }
    rows.push({ label: 'Extra questions', value: `${snapshot.question_credits ?? 0} left` });
    return rows;
  });

  protected readonly compare: CompareRow[] = [
    { label: 'Ask answers', free: '1 to try', plus: '5 a month', practitioner: '15 a month' },
    { label: 'Profiles', free: '1', plus: '3', practitioner: '10' },
    { label: 'Yogas', free: '2', plus: 'All', practitioner: 'All' },
    { label: 'What each dosha means', free: false, plus: true, practitioner: true },
    { label: 'Compatibility', free: 'Score, 1 a month', plus: 'Full report', practitioner: 'Full report' },
    { label: 'Readings', free: false, plus: true, practitioner: true },
    { label: 'Remedies', free: '1 practice + one per flag', plus: 'Full plan', practitioner: 'Full plan' },
    { label: 'Muhurta', free: false, plus: true, practitioner: true },
    { label: 'Natural reading voice', free: false, plus: true, practitioner: true },
    { label: 'Divisional charts (D2–D60)', free: false, plus: false, practitioner: true },
    { label: 'Practitioner mode', free: false, plus: false, practitioner: true },
  ];

  /** Never behind a plan, so the reader can see that before choosing. */
  protected readonly alwaysFree = [
    'Today, the panchang and the calendar',
    'Your birth chart (D1) and birth signature',
    'Every dosha by name, with its cancellations',
    'Safety guidance and where to get real help',
    'Your sources, and your data to export or delete',
  ];

  ngOnInit(): void {
    this.analytics.track('plans_viewed', { from: this.route.snapshot.queryParamMap.get('from') });
    void this.load();
  }

  protected async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(false);
    try {
      const [snapshot, catalog] = await Promise.all([
        this.entitlements.snapshot(),
        this.entitlements.products(),
        this.kundlis.load().catch(() => undefined),
      ]);
      this.current.set(snapshot);
      if (snapshot.access_tier === 'plus') this.chooseFamily('pro');
      this.products.set(catalog.products);
      void this.store.init(catalog.products);
    } catch {
      this.error.set(true);
    } finally {
      this.loading.set(false);
    }
    if (this.route.snapshot.queryParamMap.get('focus') === 'packs') {
      setTimeout(() => this.packsSection()?.nativeElement.scrollIntoView({ block: 'start', behavior: 'smooth' }));
    }
  }

  protected price(product: StoreProduct): string {
    return this.store.prices()[product.id] ?? `₹${product.price_inr.toLocaleString('en-IN')}`;
  }

  protected planCadence(product: StoreProduct): string {
    return product.months === 12 ? 'a year' : 'a month';
  }

  /** Yearly against twelve monthly payments, from the server's launch prices. */
  protected readonly yearlySaving = computed(() => {
    const monthly = this.plans().find((p) => p.months === 1);
    const yearly = this.plans().find((p) => p.months === 12);
    if (!monthly || !yearly) return null;
    return Math.round((1 - yearly.price_inr / (monthly.price_inr * 12)) * 100);
  });

  protected planLabel(plan: EntitlementSnapshot): string {
    const tier = plan.access_tier[0].toUpperCase() + plan.access_tier.slice(1);
    return plan.account_topology === 'family' ? `${tier} Family` : tier;
  }

  protected planSummary(plan: EntitlementSnapshot): string {
    if (plan.status === 'grace') {
      return 'The store could not take the last payment. Your plan stays on while you update it in the store.';
    }
    if (plan.access_tier !== 'free' && plan.expires_at) {
      const date = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })
        .format(new Date(plan.expires_at.endsWith('Z') ? plan.expires_at : `${plan.expires_at}Z`));
      // Google Play's payments policy: no link or pointer to buying outside the app,
      // only the plain fact that this plan is managed where it was bought.
      return plan.source === 'razorpay'
        ? `Renews or ends on ${date}. This plan was not bought in Google Play, so it is managed where you bought it.`
        : `Renews or ends on ${date}, as set in your store account.`;
    }
    if (plan.access_tier === 'plus') return 'Deeper guidance, more answers and more profiles.';
    if (plan.access_tier === 'pro') return 'Everything in Plus, with the practitioner workflow.';
    return 'Core guidance, safety, sources and your own data, free for good.';
  }

  protected storeNote(): string | null {
    switch (this.store.unavailableReason()) {
      case 'web':
        return 'Plans are bought in the Siddha app on your phone, through Google Play or the App Store.';
      case 'not_configured':
        return 'Plans can be bought once Siddha is live in Google Play and the App Store.';
      case 'failed':
        return 'The store did not answer. Check your connection and open Plans again.';
      default:
        return null;
    }
  }

  protected async buy(productId: string): Promise<void> {
    this.busy.set(productId);
    this.notice.set(null);
    try {
      const outcome = await this.store.purchase(productId);
      if (outcome === 'cancelled') return;
      if (outcome === 'purchased') {
        this.notice.set({ tone: 'good', text: 'Done. Your purchase is active.' });
      } else {
        this.notice.set({
          tone: 'info',
          text: 'The store has your purchase. It can take a minute to show here; open Plans again shortly.',
        });
      }
      this.current.set(this.entitlements.current());
    } catch (error) {
      this.notice.set({ tone: 'bad', text: (error as Error).message });
    } finally {
      this.busy.set(null);
    }
  }

  protected async restore(): Promise<void> {
    this.busy.set('restore');
    this.notice.set(null);
    try {
      const changed = await this.store.restore();
      this.current.set(this.entitlements.current());
      this.notice.set(changed
        ? { tone: 'good', text: 'Your purchases are restored.' }
        : { tone: 'info', text: 'No earlier purchases were found for this store account.' });
    } catch {
      this.notice.set({ tone: 'bad', text: 'The store could not restore purchases just now. Try again.' });
    } finally {
      this.busy.set(null);
    }
  }

  protected openLegal(doc: 'terms' | 'privacy'): void {
    void openLegal(doc);
  }

  protected async manage(): Promise<void> {
    const url = this.store.manageUrl();
    if (Capacitor.isNativePlatform()) await Browser.open({ url });
    else window.open(url, '_blank', 'noopener');
  }
}
