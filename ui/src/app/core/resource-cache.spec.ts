import {
  ResourceCacheEnvelope,
  ResourceCacheIdentity,
  resourceCacheKey,
  resourceFreshness,
} from './resource-cache';

describe('resource cache contract', () => {
  const identity: ResourceCacheIdentity = {
    userId: 'user-a',
    profileId: 'profile-a',
    resource: 'calendar',
    schemaVersion: 1,
    profileRevision: 'birth-v3',
    date: '2026-08-14',
    timezone: 'Asia/Singapore',
    city: 'Singapore',
    nation: 'Singapore',
    ayanamsha: 'lahiri',
    nodeType: 'true',
    convention: 'amanta',
    variant: '45d:balanced',
  };

  it('creates a deterministic key independent of object insertion order', () => {
    const reordered: ResourceCacheIdentity = {
      resource: identity.resource,
      profileId: identity.profileId,
      userId: identity.userId,
      schemaVersion: identity.schemaVersion,
      variant: identity.variant,
      convention: identity.convention,
      nodeType: identity.nodeType,
      ayanamsha: identity.ayanamsha,
      nation: identity.nation,
      city: identity.city,
      timezone: identity.timezone,
      date: identity.date,
      profileRevision: identity.profileRevision,
    };

    expect(resourceCacheKey(reordered)).toBe(resourceCacheKey(identity));
  });

  it('isolates resources by account, profile, revision, location, and convention', () => {
    const baseline = resourceCacheKey(identity);
    const dimensions: Array<keyof ResourceCacheIdentity> = [
      'userId',
      'profileId',
      'profileRevision',
      'timezone',
      'city',
      'nation',
      'ayanamsha',
      'nodeType',
      'convention',
      'variant',
    ];

    for (const field of dimensions) {
      expect(resourceCacheKey({ ...identity, [field]: `${identity[field]}-changed` }))
        .withContext(field)
        .not.toBe(baseline);
    }
  });

  it('rejects cache identities that could leak across users or profiles', () => {
    expect(() => resourceCacheKey({ ...identity, userId: '' })).toThrowError(/userId/);
    expect(() => resourceCacheKey({ ...identity, profileId: '' })).toThrowError(/profileId/);
    expect(() => resourceCacheKey({ ...identity, schemaVersion: 0 })).toThrowError(/schemaVersion/);
  });

  it('distinguishes fresh, stale-usable, and expired data at exact boundaries', () => {
    const envelope: ResourceCacheEnvelope<object> = {
      identity,
      payload: {},
      storedAt: 1_000,
      staleAt: 2_000,
      expiresAt: 3_000,
      source: 'network',
    };

    expect(resourceFreshness(envelope, 1_999)).toBe('fresh');
    expect(resourceFreshness(envelope, 2_000)).toBe('stale');
    expect(resourceFreshness(envelope, 2_999)).toBe('stale');
    expect(resourceFreshness(envelope, 3_000)).toBe('expired');
  });
});
