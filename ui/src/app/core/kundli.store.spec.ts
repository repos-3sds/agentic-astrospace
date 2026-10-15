import { TestBed } from '@angular/core/testing';

import { ApiService } from './api.service';
import { KundliStore } from './kundli.store';
import { VedicService } from './vedic.service';

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
