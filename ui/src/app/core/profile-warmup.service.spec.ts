import { DestroyRef, signal } from '@angular/core';
import { TestBed, fakeAsync, flushMicrotasks, tick } from '@angular/core/testing';

import { ConnectivityService } from './connectivity.service';
import { KundliStore } from './kundli.store';
import { PreferencesService } from './preferences.service';
import { PROFILE_WARMUP_DELAY_MS, ProfileWarmupService } from './profile-warmup.service';
import { VedicService } from './vedic.service';

describe('ProfileWarmupService', () => {
  let vedic: jasmine.SpyObj<VedicService>;
  let store: { loaded: ReturnType<typeof signal<boolean>>; activeId: ReturnType<typeof signal<string | null>>; kundlis: ReturnType<typeof signal<{ id: string }[]>> };
  let connectivity: { state: ReturnType<typeof signal<string>> };
  let destroyCallbacks: (() => void)[];

  beforeEach(() => {
    vedic = jasmine.createSpyObj<VedicService>('VedicService', ['dailyGuidance', 'all']);
    vedic.dailyGuidance.and.resolveTo({} as never);
    vedic.all.and.resolveTo({} as never);
    store = {
      loaded: signal(true),
      activeId: signal<string | null>('me'),
      kundlis: signal([{ id: 'me' }, { id: 'mum' }, { id: 'son' }]),
    };
    connectivity = { state: signal('online') };
    destroyCallbacks = [];
    TestBed.configureTestingModule({
      providers: [
        { provide: VedicService, useValue: vedic },
        { provide: KundliStore, useValue: store },
        { provide: ConnectivityService, useValue: connectivity },
        {
          provide: PreferencesService,
          useValue: { panchangaContextKey: signal('k'), ayanamsha: signal('lahiri'), nodeType: signal('mean') },
        },
      ],
    });
  });

  function start(): void {
    const destroyRef = { onDestroy: (fn: () => void) => destroyCallbacks.push(fn) } as unknown as DestroyRef;
    TestBed.inject(ProfileWarmupService).start(destroyRef);
    TestBed.tick();
  }

  afterEach(() => destroyCallbacks.forEach((fn) => fn()));

  it('warms every other saved profile, after the open one has gone first', fakeAsync(() => {
    start();
    tick(PROFILE_WARMUP_DELAY_MS - 1);
    expect(vedic.dailyGuidance).not.toHaveBeenCalled();
    tick(1);
    flushMicrotasks();
    expect(vedic.dailyGuidance.calls.allArgs()).toEqual([['mum'], ['son']]);
    expect(vedic.all.calls.allArgs()).toEqual([['mum'], ['son']]);
  }));

  it('fetches one profile at a time', fakeAsync(() => {
    let finishMum!: () => void;
    vedic.dailyGuidance.and.callFake((id: string) =>
      id === 'mum' ? new Promise((resolve) => (finishMum = () => resolve({} as never))) : Promise.resolve({} as never));
    start();
    tick(PROFILE_WARMUP_DELAY_MS);
    flushMicrotasks();
    expect(vedic.dailyGuidance.calls.allArgs()).toEqual([['mum']]);
    finishMum();
    flushMicrotasks();
    expect(vedic.dailyGuidance.calls.allArgs()).toEqual([['mum'], ['son']]);
  }));

  it('does nothing offline', fakeAsync(() => {
    connectivity.state.set('offline');
    start();
    tick(PROFILE_WARMUP_DELAY_MS * 2);
    flushMicrotasks();
    expect(vedic.dailyGuidance).not.toHaveBeenCalled();
  }));

  it('starts over after a switch, leaving out the newly open profile', fakeAsync(() => {
    start();
    tick(PROFILE_WARMUP_DELAY_MS / 2);
    store.activeId.set('mum');
    TestBed.tick();
    tick(PROFILE_WARMUP_DELAY_MS);
    flushMicrotasks();
    expect(vedic.dailyGuidance.calls.allArgs()).toEqual([['me'], ['son']]);
  }));

  it('skips a profile removed while it waited', fakeAsync(() => {
    start();
    store.kundlis.set([{ id: 'me' }, { id: 'son' }]);
    // Removing reschedules too; either way 'mum' is never asked for.
    TestBed.tick();
    tick(PROFILE_WARMUP_DELAY_MS);
    flushMicrotasks();
    expect(vedic.dailyGuidance.calls.allArgs()).toEqual([['son']]);
  }));
});
