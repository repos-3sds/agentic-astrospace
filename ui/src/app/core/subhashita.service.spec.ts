import { TestBed } from '@angular/core/testing';

import { ApiService } from './api.service';
import { localIsoDate, SubhashitaService } from './subhashita.service';

describe('SubhashitaService', () => {
  const today = localIsoDate();
  const day = (date: string) => ({ date, id: `v-${date}`, source: 'Chanakya Niti', ref: '1.1', sanskrit: 'धर्म', english: 'A verse for the day.' });
  let calls: string[];

  function make(): SubhashitaService {
    calls = [];
    TestBed.configureTestingModule({
      providers: [{
        provide: ApiService,
        useValue: { get: (path: string) => { calls.push(path); return Promise.resolve({ items: [day(today)] }); } },
      }],
    });
    return TestBed.inject(SubhashitaService);
  }

  beforeEach(() => localStorage.clear());

  it('asks for the reader’s own date and shows only today’s verse', async () => {
    localStorage.setItem('astrospace.subhashita.days', JSON.stringify([day('2000-01-01')]));
    const service = make();
    const verse = await service.load();
    expect(calls).toEqual([`/subhashita?start=${today}&days=14`]);
    expect(verse?.date).toBe(today);
    expect(service.upcoming().map((v) => v.date)).toEqual([today]);
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
