import { TestBed } from '@angular/core/testing';

import { ApiService } from './api.service';
import { PreferencesService } from './preferences.service';
import { VedicService } from './vedic.service';

describe('VedicService location-sensitive caches', () => {
  let api: jasmine.SpyObj<ApiService>;
  let prefs: PreferencesService;
  let service: VedicService;

  beforeEach(() => {
    localStorage.clear();
    api = jasmine.createSpyObj<ApiService>('ApiService', ['get', 'put']);
    api.get.and.callFake(async (path: string) => {
      if (path.includes('/daily?')) return { date: '2026-08-11' } as any;
      return {
        start_date: '2026-08-11',
        end_date: '2026-09-24',
        place: { city: 'Singapore' },
        panchanga_days: [],
        by_date: {},
      } as any;
    });
    api.put.and.resolveTo({} as any);
    TestBed.configureTestingModule({
      providers: [
        VedicService,
        PreferencesService,
        { provide: ApiService, useValue: api },
      ],
    });
    prefs = TestBed.inject(PreferencesService);
    service = TestBed.inject(VedicService);
  });

  it('uses city, nation and timezone in daily guidance identity and refetches after a place change', async () => {
    prefs.timezoneMode.set('panchanga_place');
    prefs.setPanchangaPlace({ city: 'Singapore', nation: 'SG', timezone: 'Asia/Singapore', label: 'Singapore' } as any);

    await service.dailyGuidance('profile-1');
    expect(api.get.calls.mostRecent().args[0]).toContain('city=Singapore');
    expect(api.get.calls.mostRecent().args[0]).toContain('timezone=Asia%2FSingapore');
    expect(service.cachedDailyGuidance('profile-1')).not.toBeNull();

    prefs.setPanchangaPlace({ city: 'Kakinada', nation: 'IN', timezone: 'Asia/Kolkata', label: 'Kakinada' } as any);
    expect(service.cachedDailyGuidance('profile-1')).toBeNull();
    await service.dailyGuidance('profile-1');

    expect(api.get).toHaveBeenCalledTimes(2);
    expect(api.get.calls.mostRecent().args[0]).toContain('city=Kakinada');
    expect(api.get.calls.mostRecent().args[0]).toContain('timezone=Asia%2FKolkata');
  });

  it('changes the reactive panchanga context key when current location changes', () => {
    prefs.timezoneMode.set('panchanga_place');
    prefs.setPanchangaPlace({ city: 'Singapore', nation: 'SG', timezone: 'Asia/Singapore', label: 'Singapore' } as any);
    const first = prefs.panchangaContextKey();

    prefs.setPanchangaPlace({ city: 'Chennai', nation: 'IN', timezone: 'Asia/Kolkata', label: 'Chennai' } as any);

    expect(prefs.panchangaContextKey()).not.toBe(first);
    expect(prefs.panchangaContextKey()).toContain('Chennai');
  });
});
