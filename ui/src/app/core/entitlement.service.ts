import { Injectable, inject } from '@angular/core';
import { ApiService } from './api.service';

export type AccessTier = 'free' | 'plus' | 'pro';

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

  snapshot(): Promise<EntitlementSnapshot> {
    return this.api.get<EntitlementSnapshot>('/entitlements');
  }

  catalog(): Promise<EntitlementCatalog> {
    return this.api.get<EntitlementCatalog>('/entitlements/catalog');
  }
}
