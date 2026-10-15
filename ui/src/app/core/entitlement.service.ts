import { Injectable, computed, inject, signal } from '@angular/core';
import { ApiService } from './api.service';
import { AccessTier } from './entitlement-denial';

export { EntitlementLimitError, isEntitlementDenial } from './entitlement-denial';
export type { AccessTier, EntitlementDenial } from './entitlement-denial';


export interface EntitlementSnapshot {
  account_id: string;
  access_tier: AccessTier;
  account_topology: 'individual' | 'family';
  offer_code: string | null;
  status: string;
  source: string;
  effective_at: string;
  expires_at: string | null;
  grace_ends_at: string | null;
  revision: number;
  catalog_revision: number;
  entitlements: Record<string, boolean | number | null>;
  usage: Record<string, {
    used: number;
    reserved: number;
    remaining: number | null;
    resets_at: string;
    period_id: string;
  }>;
  /** Unspent question-pack credits, used after the monthly allowance. */
  question_credits?: number;
  /** Whether a reached limit blocks. Off until store purchases are live. */
  quotas_enforced?: boolean;
}

export interface StoreProduct {
  id: string;
  kind: 'plan' | 'question_pack';
  title: string;
  price_inr: number;
  tier: AccessTier | null;
  months: number | null;
  questions: number | null;
}

/** Where a limit stands, for a meter: null when there is no limit to show. */
export interface Allowance {
  limit: number;
  used: number;
  remaining: number;
  credits: number;
  resetsAt: string | null;
  enforced: boolean;
}

export interface EntitlementCatalog {
  revision: number;
  capabilities: Record<string, {
    kind: 'flag' | 'limit';
    description: string;
    protected_baseline: boolean;
  }>;
}

@Injectable({ providedIn: 'root' })
export class EntitlementService {
  private readonly api = inject(ApiService);

  /** The last snapshot fetched, for meters and gates that should not refetch. */
  readonly current = signal<EntitlementSnapshot | null>(null);

  /** Ask answers this month. */
  readonly askAllowance = computed<Allowance | null>(() => {
    const snapshot = this.current();
    const limit = snapshot?.entitlements['ask.answers.period'];
    if (!snapshot || typeof limit !== 'number') return null;
    const usage = snapshot.usage['ask.answers.period'];
    const used = (usage?.used ?? 0) + (usage?.reserved ?? 0);
    return {
      limit,
      used,
      remaining: Math.max(0, limit - used),
      credits: snapshot.question_credits ?? 0,
      resetsAt: usage?.resets_at ?? null,
      enforced: !!snapshot.quotas_enforced,
    };
  });

  async snapshot(): Promise<EntitlementSnapshot> {
    const snapshot = await this.api.get<EntitlementSnapshot>('/entitlements');
    this.current.set(snapshot);
    return snapshot;
  }

  /** Refresh quietly; a meter is never worth an error card. */
  async refresh(): Promise<void> {
    try {
      await this.snapshot();
    } catch {
      // Keep the last snapshot.
    }
  }

  products(): Promise<{ products: StoreProduct[]; quotas_enforced: boolean }> {
    return this.api.get('/entitlements/products');
  }

  catalog(): Promise<EntitlementCatalog> {
    return this.api.get<EntitlementCatalog>('/entitlements/catalog');
  }
}
