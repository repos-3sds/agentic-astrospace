import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { ApiService } from './api.service';
import { AuthService } from './auth.service';
import { localIsoDate, SubhashitaService } from './subhashita.service';

describe('SubhashitaService', () => {
  const today = localIsoDate();
  const day = (date: string) => ({ date, id: `v-${date}`, source: 'Chanakya Niti', ref: '1.1', sanskrit: 'धर्म', english: 'A verse for the day.', meaning: 'A plain line.' });
  let calls: string[];
  /** Whose rotation the fake server says it served; the asking account unless set. */
  let served: string | null | undefined;

  function make(userId = 'reader-1'): SubhashitaService {
    calls = [];
    TestBed.configureTestingModule({
      providers: [{
        provide: ApiService,
        useValue: {
          get: (path: string) => { calls.push(path); return Promise.resolve({ items: [day(today)], reader: served === undefined ? userId : served }); },
        },
      }, { provide: AuthService, useValue: { user: signal({ id: userId }) } }],
    });
    return TestBed.inject(SubhashitaService);
  }

  beforeEach(() => { localStorage.clear(); served = undefined; });

  it('asks for the reader’s own date and shows only today’s verse', async () => {
    localStorage.setItem('astrospace.subhashita.days', JSON.stringify([day('2000-01-01')]));
    const service = make();
    const verse = await service.load();
    expect(calls).toEqual([`/subhashita?start=${today}&days=14`]);
    expect(verse?.date).toBe(today);
    expect(service.upcoming().map((v) => v.date)).toEqual([today]);
  });

  it('keeps a reader’s own verses, and refetches for another account', async () => {
    const ahead = Array.from({ length: 14 }, (_, n) => {
      const d = new Date(); d.setDate(d.getDate() + n); return day(localIsoDate(d));
    });
    localStorage.setItem('astrospace.subhashita.days', JSON.stringify(ahead));
    localStorage.setItem('astrospace.subhashita.daysFrom', 'reader-1');
    await make('reader-1').load();
    expect(calls).toEqual([]);
    TestBed.resetTestingModule();
    await make('reader-2').load();
    expect(calls).toEqual([`/subhashita?start=${today}&days=14`]);
    expect(localStorage.getItem('astrospace.subhashita.daysFrom')).toBe('reader-2');
  });

  it('files a run under the rotation the server served, so a shared run is fetched again', async () => {
    served = null; // the server did not use the reader's account
    await make('reader-1').load();
    expect(localStorage.getItem('astrospace.subhashita.daysFrom')).toBe('');
    const ahead = Array.from({ length: 14 }, (_, n) => {
      const d = new Date(); d.setDate(d.getDate() + n); return day(localIsoDate(d));
    });
    localStorage.setItem('astrospace.subhashita.days', JSON.stringify(ahead));
    TestBed.resetTestingModule();
    served = undefined;
    await make('reader-1').load();
    expect(calls).toEqual([`/subhashita?start=${today}&days=14`]);
    expect(localStorage.getItem('astrospace.subhashita.daysFrom')).toBe('reader-1');
  });

  it('offers the verse once a day, and not on a reader’s first day', () => {
    const service = make();
    expect(service.neverOffered()).toBeTrue();
    service.markSeen();
    expect(service.neverOffered()).toBeFalse();
    expect(service.unseenToday()).toBeFalse();
    localStorage.setItem('astrospace.subhashita.seenOn', '2000-01-01');
    expect(service.unseenToday()).toBeTrue();
  });
});
