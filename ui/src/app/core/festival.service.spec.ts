import { TestBed } from '@angular/core/testing';

import { ApiService } from './api.service';
import { FestivalService } from './festival.service';

describe('FestivalService stored windows', () => {
  const place = { city: 'Hyderabad', nation: 'IN' };
  const payload = (name: string) => ({ count: 1, festivals: [{ name, regions: ['pan-india'] }] }) as never;
  let get: jasmine.Spy;

  function service(): FestivalService {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [{ provide: ApiService, useValue: { get } }] });
    return TestBed.inject(FestivalService);
  }

  beforeEach(() => {
    Object.keys(localStorage)
      .filter((key) => key.startsWith('astrospace.festivals:'))
      .forEach((key) => localStorage.removeItem(key));
    get = jasmine.createSpy('get');
  });

  afterEach(() => jasmine.clock().uninstall());

  it('ignores windows stored by the old forever-cache', () => {
    localStorage.setItem('astrospace.festivals:v1:city=Hyderabad&nation=IN&from_date=2026-10-01&days=31',
      JSON.stringify(payload('Vijayadashami on the 21st')));
    expect(service().cachedUpcoming(place, '2026-10-01', 31)).toBeNull();
  });

  it('serves a stored window for a day, then asks the server again', async () => {
    jasmine.clock().install();
    jasmine.clock().mockDate(new Date('2026-10-20T06:00:00Z'));
    get.and.resolveTo(payload('first'));
    await service().upcoming(place, '2026-10-01', 31);

    expect(service().cachedUpcoming(place, '2026-10-01', 31)?.festivals[0].name).toBe('first');

    jasmine.clock().mockDate(new Date('2026-10-21T07:00:00Z'));
    expect(service().cachedUpcoming(place, '2026-10-01', 31)).toBeNull();
  });

  it('falls back to a stale copy when the server cannot be reached', async () => {
    jasmine.clock().install();
    jasmine.clock().mockDate(new Date('2026-10-18T06:00:00Z'));
    get.and.resolveTo(payload('stale'));
    await service().upcoming(place, '2026-10-01', 31);

    jasmine.clock().mockDate(new Date('2026-10-20T06:00:00Z'));
    get.and.rejectWith(new Error('offline'));
    const result = await service().upcoming(place, '2026-10-01', 31);
    expect(result.festivals[0].name).toBe('stale');
  });
});
