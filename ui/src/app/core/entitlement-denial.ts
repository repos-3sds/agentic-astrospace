/**
 * The 402 a plan or limit returns (`main.py`'s EntitlementDenied handler),
 * kept apart from EntitlementService so ApiService can recognise it without
 * an import cycle.
 */
export type AccessTier = 'free' | 'plus' | 'pro';

/** The 402 body the API returns when a plan or limit stops a request. */
export interface EntitlementDenial {
  code: 'entitlement_required' | 'entitlement_limit_reached';
  entitlement: string;
  access_tier: AccessTier;
  remaining: number | null;
  /** The monthly allowance that ran out; absent from older servers. */
  limit?: number | null;
  resets_at: string | null;
  upgrade_options: AccessTier[];
}

export class EntitlementLimitError extends Error {
  override readonly name = 'EntitlementLimitError';
  constructor(readonly denial: EntitlementDenial) {
    super(denial.code === 'entitlement_limit_reached'
      ? 'You have used this month’s allowance.'
      : 'This needs a plan.');
  }
}

export function isEntitlementDenial(value: unknown): value is EntitlementDenial {
  const code = (value as EntitlementDenial | null)?.code;
  return code === 'entitlement_required' || code === 'entitlement_limit_reached';
}

