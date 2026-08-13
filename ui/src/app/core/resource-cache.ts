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
  source: 'network' | 'migration';
}

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
