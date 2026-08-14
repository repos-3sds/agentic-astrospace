export type ResourceFreshness = 'fresh' | 'stale' | 'expired';

export interface ResourceCacheIdentity {
  userId: string;
  profileId: string;
  resource: string;
  schemaVersion: number;
  profileRevision?: string | null;
  date?: string | null;
  timezone?: string | null;
  city?: string | null;
  nation?: string | null;
  ayanamsha?: string | null;
  nodeType?: string | null;
  convention?: string | null;
  variant?: string | null;
}

export interface ResourceCacheEnvelope<T> {
  identity: ResourceCacheIdentity;
  payload: T;
  storedAt: number;
  staleAt: number;
  expiresAt: number;
  engineVersion?: string;
  datasetVersion?: string;
  source: 'network' | 'migration';
}

export interface ResourceCacheMetadata {
  engineVersion?: string | null;
  datasetVersion?: string | null;
  /** Authoritative server boundary, such as next local sunrise. */
  validUntil?: string | null;
}

export interface ResourceCacheVersionExpectation {
  engineVersion?: string;
  datasetVersion?: string;
}

export interface ResourceCachePolicy {
  staleAfterMs: number;
  expireAfterMs: number;
}

export interface CachedResource<T> {
  data: T;
  freshness: ResourceFreshness;
  storedAt: number;
  expiresAt: number;
}

export const TODAY_CACHE_POLICY: ResourceCachePolicy = {
  staleAfterMs: 15 * 60 * 1000,
  expireAfterMs: 36 * 60 * 60 * 1000,
};

export const CALENDAR_CACHE_POLICY: ResourceCachePolicy = {
  staleAfterMs: 6 * 60 * 60 * 1000,
  expireAfterMs: 45 * 24 * 60 * 60 * 1000,
};

const IDENTITY_FIELDS: ReadonlyArray<keyof ResourceCacheIdentity> = [
  'userId',
  'profileId',
  'resource',
  'schemaVersion',
  'profileRevision',
  'date',
  'timezone',
  'city',
  'nation',
  'ayanamsha',
  'nodeType',
  'convention',
  'variant',
];

/** Builds one deterministic key shared by memory, web, and native stores. */
export function resourceCacheKey(identity: ResourceCacheIdentity): string {
  assertRequiredIdentity(identity);
  const normalized = IDENTITY_FIELDS.map((field) => [field, normalize(identity[field])]);
  return normalized
    .filter(([, value]) => value !== '')
    .map(([field, value]) => `${field}=${encodeURIComponent(value)}`)
    .join('&');
}

export function resourceFreshness(
  envelope: Pick<ResourceCacheEnvelope<unknown>, 'staleAt' | 'expiresAt'>,
  now = Date.now(),
): ResourceFreshness {
  if (now >= envelope.expiresAt) return 'expired';
  if (now >= envelope.staleAt) return 'stale';
  return 'fresh';
}

function normalize(value: ResourceCacheIdentity[keyof ResourceCacheIdentity]): string {
  if (value === null || value === undefined) return '';
  return String(value).trim().normalize('NFKC');
}

function assertRequiredIdentity(identity: ResourceCacheIdentity): void {
  for (const field of ['userId', 'profileId', 'resource'] as const) {
    if (!normalize(identity[field])) throw new Error(`Cache identity requires ${field}`);
  }
  if (!Number.isInteger(identity.schemaVersion) || identity.schemaVersion < 1) {
    throw new Error('Cache identity requires a positive schemaVersion');
  }
}
