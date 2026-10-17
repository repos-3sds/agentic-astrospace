import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { ApiService } from './api.service';
import { AuthService } from './auth.service';
import { ConnectivityService, ConnectivityState } from './connectivity.service';
import { KundliStore } from './kundli.store';
import { Kundli } from './models';
import { ResourceCacheService } from './resource-cache.service';
import { RESOURCE_CACHE_PERSISTENCE, WebResourceCachePersistence } from './resource-cache.persistence';
import { SessionTeardown } from './session-teardown';
import { VedicService } from './vedic.service';

const asha = { id: 'k1', name: 'Asha', user_id: 'u1', updated_at: '2026-10-01' } as Kundli;
const ravi = { id: 'k2', name: 'Ravi', user_id: 'u1', updated_at: '2026-10-01' } as Kundli;

/** Lets pending promise callbacks (and signal effects) run. */
async function settle(): Promise<void> {
  for (let i = 0; i < 5; i++) await Promise.resolve();
  TestBed.tick();
  for (let i = 0; i < 5; i++) await Promise.resolve();
}

describe('KundliStore offline cold start', () => {
  let api: jasmine.SpyObj<ApiService>;
  let state: ReturnType<typeof signal<ConnectivityState>>;
  let cache: ResourceCacheService;

  async function boot(): Promise<KundliStore> {
    TestBed.configureTestingModule({
      providers: [
        { provide: ApiService, useValue: api },
        { provide: AuthService, useValue: { user: signal({ id: 'u1' }) } },
        { provide: ConnectivityService, useValue: { state } },
        { provide: RESOURCE_CACHE_PERSISTENCE, useValue: new WebResourceCachePersistence() },
        {
          provide: VedicService,
          useValue: jasmine.createSpyObj('VedicService', [
            'configureProfile',
            'clearConfiguredProfiles',
            'invalidate',
            'removeConfiguredProfile',
          ]),
        },
      ],
    });
    cache = TestBed.inject(ResourceCacheService);
    await cache.initialize();
    return TestBed.inject(KundliStore);
  }

  beforeEach(() => {
    localStorage.clear();
    api = jasmine.createSpyObj<ApiService>('ApiService', ['get', 'post', 'patch', 'delete']);
    state = signal<ConnectivityState>('online');
  });

  afterEach(() => localStorage.clear());

  it('takes the self profile as the owner, else the first one made', async () => {
    const mine = { ...asha, relation: 'relative', created_at: '2026-09-01' } as Kundli;
    const friend = { ...ravi, relation: 'friend', created_at: '2026-10-01' } as Kundli;
    api.get.and.resolveTo([friend, mine]);
    const store = await boot();
    await store.load();
    expect(store.owner()?.id).toBe('k1');

    store.kundlis.set([{ ...friend, relation: 'self' }, mine]);
    expect(store.owner()?.id).toBe('k2');
  });

  it('caches the profile list after a network load', async () => {
    api.get.and.resolveTo([asha, ravi]);
    const store = await boot();

    await store.load();
    await cache.flush();

    expect(store.kundlis()).toEqual([asha, ravi]);
    expect(Object.keys(localStorage).some((key) => key.includes('resource=profile-list'))).toBeTrue();
  });

  it('shows cached profiles at once on an offline launch, without an error', async () => {
    api.get.and.resolveTo([asha, ravi]);
    const first = await boot();
    await first.load();
    await cache.flush();
    TestBed.resetTestingModule();

    // Relaunch with no network: the request fails, the cached list stands.
    api.get.and.rejectWith(new TypeError('Failed to fetch'));
    state.set('offline');
    const store = await boot();

    await store.load();
    await settle();

    expect(store.kundlis().map((k) => k.name)).toEqual(['Asha', 'Ravi']);
    expect(store.loaded()).toBeTrue();
    expect(store.loadError()).toBeNull();
    expect(store.activeId()).toBe('k1');
  });

  it('revalidates in the background and refreshes when the connection returns', async () => {
    api.get.and.resolveTo([asha]);
    const first = await boot();
    await first.load();
    await cache.flush();
    TestBed.resetTestingModule();

    api.get.and.rejectWith(new TypeError('Failed to fetch'));
    state.set('offline');
    const store = await boot();
    await store.load();
    await settle();
    expect(store.kundlis()).toEqual([asha]);

    api.get.and.resolveTo([asha, ravi]);
    state.set('online');
    await settle();

    expect(store.kundlis()).toEqual([asha, ravi]);
  });

  it('retries a first load that failed once the connection returns', async () => {
    api.get.and.rejectWith(new TypeError('Failed to fetch'));
    state.set('offline');
    const store = await boot();

    await expectAsync(store.load()).toBeRejected();
    expect(store.loadError()).not.toBeNull();

    api.get.and.resolveTo([ravi]);
    state.set('online');
    await settle();

    expect(store.kundlis()).toEqual([ravi]);
    expect(store.loadError()).toBeNull();
  });

  it('forgets the list, selection and cache on sign-out', async () => {
    api.get.and.resolveTo([asha, ravi]);
    const store = await boot();
    await store.load();
    store.setActive('k2');
    await cache.flush();

    TestBed.inject(SessionTeardown).run();
    await cache.flush();

    expect(store.kundlis()).toEqual([]);
    expect(store.activeId()).toBeNull();
    expect(store.loaded()).toBeFalse();
    expect(localStorage.getItem('astrospace.activeKundliId')).toBeNull();
    expect(Object.keys(localStorage).some((key) => key.includes('resource=profile-list'))).toBeFalse();
  });
});

describe('KundliStore.create', () => {
  let store: KundliStore;
  let next = 0;

  beforeEach(() => {
    next = 0;
    localStorage.removeItem('astrospace.activeKundliId');
    TestBed.configureTestingModule({
      providers: [
        { provide: ApiService, useValue: { post: async (_: string, body: any) => ({ id: `k${++next}`, ...body }) } },
        { provide: VedicService, useValue: { configureProfile: () => undefined } },
        // No session: the profile-list cache is owned by the local stand-in.
        { provide: AuthService, useValue: { user: () => null } },
      ],
    });
    store = TestBed.inject(KundliStore);
  });

  it('makes the first profile active', async () => {
    await store.create({ name: 'Me' } as any, { activate: false });
    expect(store.activeId()).toBe('k1');
  });

  it('adds a family member without switching the app to them', async () => {
    await store.create({ name: 'Me' } as any);
    await store.create({ name: 'Partner' } as any, { activate: false });
    expect(store.activeId()).toBe('k1');
    expect(store.kundlis().map((k) => k.name)).toEqual(['Me', 'Partner']);
  });
});
