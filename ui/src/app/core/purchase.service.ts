import { Injectable, inject, signal } from '@angular/core';
import { Capacitor } from '@capacitor/core';

import { environment } from '../../environments/environment';
import { AnalyticsService } from './analytics.service';
import { AuthService } from './auth.service';
import { EntitlementService, StoreProduct } from './entitlement.service';

export type PurchaseOutcome = 'purchased' | 'pending' | 'cancelled';

/** Why buying is not possible here, said plainly on the Plans screen. */
export type StoreUnavailableReason = 'web' | 'not_configured' | 'failed';

/**
 * Store purchases through RevenueCat (D5).
 *
 * The phone only starts the purchase. What the reader is entitled to comes
 * from the server, which learns about it from RevenueCat's webhook
 * (`api/store_routes.py`), so after a purchase this polls the entitlement
 * snapshot until the plan or credits appear rather than unlocking anything
 * locally.
 *
 * RevenueCat's app user id is the Supabase user id (`logIn`), which is what
 * the webhook carries back as `app_user_id`.
 */
@Injectable({ providedIn: 'root' })
export class PurchaseService {
  private readonly auth = inject(AuthService);
  private readonly entitlements = inject(EntitlementService);
  private readonly analytics = inject(AnalyticsService);

  readonly available = signal(false);
  readonly unavailableReason = signal<StoreUnavailableReason | null>(null);
  /** The store's own localised price per product id, once fetched. */
  readonly prices = signal<Record<string, string>>({});

  private ready: Promise<void> | null = null;
  private storeProducts = new Map<string, unknown>();

  init(catalog: StoreProduct[]): Promise<void> {
    this.ready ??= this.configure(catalog).catch(() => {
      this.available.set(false);
      this.unavailableReason.set('failed');
      this.ready = null;
    });
    return this.ready;
  }

  async purchase(productId: string): Promise<PurchaseOutcome> {
    const product = this.storeProducts.get(productId);
    if (!this.available() || !product) throw new Error('Purchases are not available on this device yet.');
    const { Purchases } = await import('@revenuecat/purchases-capacitor');
    this.analytics.track('purchase_started', { product: productId });
    try {
      await Purchases.purchaseStoreProduct({ product: product as never });
    } catch (error) {
      if ((error as { userCancelled?: boolean }).userCancelled) return 'cancelled';
      throw new Error('The store could not complete that purchase. You have not been charged.');
    }
    const outcome = (await this.waitForServer()) ? 'purchased' : 'pending';
    this.analytics.track('purchase_completed', { product: productId, confirmed: outcome === 'purchased' });
    return outcome;
  }

  async restore(): Promise<boolean> {
    if (!this.available()) return false;
    const { Purchases } = await import('@revenuecat/purchases-capacitor');
    await Purchases.restorePurchases();
    return this.waitForServer();
  }

  /** The store's own subscription page; cancelling happens there, not here. */
  manageUrl(): string {
    return Capacitor.getPlatform() === 'ios'
      ? 'https://apps.apple.com/account/subscriptions'
      : 'https://play.google.com/store/account/subscriptions';
  }

  private async configure(catalog: StoreProduct[]): Promise<void> {
    const platform = Capacitor.getPlatform();
    if (!Capacitor.isNativePlatform()) {
      this.unavailableReason.set('web');
      return;
    }
    const apiKey = platform === 'ios' ? environment.revenueCat?.ios : environment.revenueCat?.android;
    if (!apiKey) {
      this.unavailableReason.set('not_configured');
      return;
    }
    const userId = this.auth.user()?.id;
    const { Purchases, PRODUCT_CATEGORY } = await import('@revenuecat/purchases-capacitor');
    await Purchases.configure({ apiKey, appUserID: userId ?? null });
    const ids = (kind: StoreProduct['kind']) => catalog.filter((p) => p.kind === kind).map((p) => p.id);
    const [plans, packs] = await Promise.all([
      Purchases.getProducts({ productIdentifiers: ids('plan'), type: PRODUCT_CATEGORY.SUBSCRIPTION }),
      Purchases.getProducts({ productIdentifiers: ids('question_pack'), type: PRODUCT_CATEGORY.NON_SUBSCRIPTION }),
    ]);
    const prices: Record<string, string> = {};
    for (const product of [...plans.products, ...packs.products]) {
      // Play reports subscriptions as "id:base-plan"; the catalogue uses the id.
      const id = product.identifier.split(':')[0];
      this.storeProducts.set(id, product);
      prices[id] = product.priceString;
    }
    this.prices.set(prices);
    this.available.set(this.storeProducts.size > 0);
    this.unavailableReason.set(this.storeProducts.size > 0 ? null : 'not_configured');
  }

  /** The webhook usually lands within seconds; give it about half a minute. */
  private async waitForServer(): Promise<boolean> {
    const before = this.entitlements.current();
    const beforeKey = before ? `${before.access_tier}:${before.revision}:${before.question_credits ?? 0}` : '';
    for (let attempt = 0; attempt < 10; attempt++) {
      await new Promise((resolve) => setTimeout(resolve, attempt === 0 ? 1000 : 3000));
      const now = await this.entitlements.snapshot().catch(() => null);
      if (now && `${now.access_tier}:${now.revision}:${now.question_credits ?? 0}` !== beforeKey) return true;
    }
    return false;
  }
}
