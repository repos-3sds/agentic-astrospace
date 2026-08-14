import { TestBed } from '@angular/core/testing';

import { ResourceCacheIdentity } from './resource-cache';
import { ResourceCacheService } from './resource-cache.service';

describe('ResourceCacheService', () => {
  let service: ResourceCacheService;
  const identity: ResourceCacheIdentity = {
    userId: 'user-a',
    profileId: 'profile-a',
    resource: 'today',
    schemaVersion: 1,
    profileRevision: 'revision-1',
    date: '2026-08-14',
    timezone: 'Asia/Singapore',
  };
  const policy = { staleAfterMs: 100, expireAfterMs: 300 };

  beforeEach(async () => {
    localStorage.clear();
    TestBed.configureTestingModule({ providers: [ResourceCacheService] });
    service = TestBed.inject(ResourceCacheService);
    await service.initialize();
  });

  it('persists an envelope and restores it in a new service instance', async () => {
    const now = Date.now();
    service.set(identity, { headline: 'Steady' }, policy, now);
    await service.flush();
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [ResourceCacheService] });
    const restoredService = TestBed.inject(ResourceCacheService);
    await restoredService.initialize();
    const restored = restoredService.get<{ headline: string }>(identity, now + 50);

    expect(restored?.data.headline).toBe('Steady');
    expect(restored?.freshness).toBe('fresh');
    expect(restored?.storedAt).toBe(now);
  });

  it('never returns another account or profile revision for the same resource', () => {
    service.set(identity, { private: 'profile-a reading' }, policy, 1_000);

    expect(service.get({ ...identity, userId: 'user-b' }, 1_050)).toBeNull();
    expect(service.get({ ...identity, profileId: 'profile-b' }, 1_050)).toBeNull();
    expect(service.get({ ...identity, profileRevision: 'revision-2' }, 1_050)).toBeNull();
  });

  it('deletes expired and corrupt entries rather than surfacing them', async () => {
    service.set(identity, { old: true }, policy, 1_000);
    expect(service.get(identity, 1_300)).toBeNull();

    const key = Object.keys(localStorage).find((candidate) => candidate.startsWith('siddha.resource-cache'))!;
    expect(key).toBeUndefined();

    localStorage.setItem('siddha.resource-cache:v1:corrupt', '{not-json');
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [ResourceCacheService] });
    service = TestBed.inject(ResourceCacheService);
    await service.initialize();
    service.clearAll();
    await service.flush();
    expect(localStorage.getItem('siddha.resource-cache:v1:corrupt')).toBeNull();
  });

  it('clears one user without deleting another user cache', () => {
    service.set(identity, { owner: 'a' }, policy, 1_000);
    service.set({ ...identity, userId: 'user-b' }, { owner: 'b' }, policy, 1_000);

    service.clearUser('user-a');

    expect(service.get(identity, 1_050)).toBeNull();
    expect(service.get<{ owner: string }>({ ...identity, userId: 'user-b' }, 1_050)?.data.owner).toBe('b');
  });

  it('keeps the memory value usable when persistent storage rejects the write', () => {
    spyOn(localStorage, 'setItem').and.throwError('quota exceeded');

    const cached = service.set(identity, { usable: true }, policy, 1_000);

    expect(cached.data.usable).toBeTrue();
    expect(service.get<{ usable: boolean }>(identity, 1_050)?.data.usable).toBeTrue();
  });

  it('caps expiry at an authoritative server validity boundary', () => {
    const cached = service.set(identity, { day: 'Thursday' }, policy, 1_000, 'network', {
      validUntil: new Date(1_180).toISOString(),
      engineVersion: 'daily-guidance-1.0',
    });

    expect(cached.expiresAt).toBe(1_180);
    expect(service.get(identity, 1_179, { engineVersion: 'daily-guidance-1.0' })?.data).toEqual({ day: 'Thursday' });
    expect(service.get(identity, 1_180, { engineVersion: 'daily-guidance-1.0' })).toBeNull();
  });

  it('rejects present incompatible engine or dataset versions', () => {
    service.set(identity, { old: true }, policy, 1_000, 'network', {
      engineVersion: 'daily-guidance-0.9',
      datasetVersion: 'calendar-old',
    });

    expect(service.get(identity, 1_050, { engineVersion: 'daily-guidance-1.0' })).toBeNull();
  });

  it('does not persist a response whose authoritative boundary already passed', async () => {
    const cached = service.set(identity, { late: true }, policy, 1_000, 'network', {
      validUntil: new Date(999).toISOString(),
    });
    await service.flush();

    expect(cached.freshness).toBe('expired');
    expect(service.get(identity, 1_000)).toBeNull();
  });

  it('removes legacy unscoped Today and Calendar payloads', () => {
    localStorage.setItem('astrospace.daily-guidance:v1:profile-a', '{}');
    localStorage.setItem('astrospace.calendar-intelligence:v3:profile-a', '{}');
    localStorage.setItem('unrelated', 'keep');

    service.discardLegacyUnscopedCaches();

    expect(localStorage.getItem('astrospace.daily-guidance:v1:profile-a')).toBeNull();
    expect(localStorage.getItem('astrospace.calendar-intelligence:v3:profile-a')).toBeNull();
    expect(localStorage.getItem('unrelated')).toBe('keep');
  });
});
