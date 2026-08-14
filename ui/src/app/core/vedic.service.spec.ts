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
    service.configureProfile({ id: 'profile-1', user_id: 'user-1', updated_at: '2026-08-11T00:00:00Z' });
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

  it('does not reuse guidance after the profile birth-data revision changes', async () => {
    prefs.timezoneMode.set('panchanga_place');
    prefs.setPanchangaPlace({ city: 'Singapore', nation: 'SG', timezone: 'Asia/Singapore', label: 'Singapore' } as any);
    await service.dailyGuidance('profile-1');
    expect(service.cachedDailyGuidance('profile-1')).not.toBeNull();

    service.configureProfile({ id: 'profile-1', user_id: 'user-1', updated_at: '2026-08-12T00:00:00Z' });

    expect(service.cachedDailyGuidance('profile-1')).toBeNull();
    await service.dailyGuidance('profile-1');
    expect(api.get).toHaveBeenCalledTimes(2);
  });

  it('does not resurrect hard-expired Today data from a suspended WebView memory cache', async () => {
    const clock = spyOn(Date, 'now').and.returnValue(1_000);
    await service.dailyGuidance('profile-1');

    clock.and.returnValue(1_000 + (40 * 60 * 60 * 1000));

    expect(service.cachedDailyGuidanceEntry('profile-1')).toBeNull();
    await service.dailyGuidance('profile-1');
    expect(api.get).toHaveBeenCalledTimes(2);
  });

  it('expires Today at the backend-provided next-sunrise boundary', async () => {
    const clock = spyOn(Date, 'now').and.returnValue(1_000);
    api.get.and.resolveTo({
      date: '2026-08-14',
      engine_version: 'daily-guidance-1.0',
      valid_from: new Date(900).toISOString(),
      valid_until: new Date(1_180).toISOString(),
      day_definition: 'sunrise_to_next_sunrise',
    } as any);

    await service.dailyGuidance('profile-1');
    clock.and.returnValue(1_179);
    expect(service.cachedDailyGuidanceEntry('profile-1')).not.toBeNull();

    clock.and.returnValue(1_180);
    expect(service.cachedDailyGuidanceEntry('profile-1')).toBeNull();
  });

  it('isolates the same profile id when its owning account changes', async () => {
    await service.dailyGuidance('profile-1');
    service.configureProfile({ id: 'profile-1', user_id: 'user-2', updated_at: '2026-08-11T00:00:00Z' });

    expect(service.cachedDailyGuidance('profile-1')).toBeNull();
  });

  it('keeps Calendar cache identities separate by place and practitioner depth', async () => {
    prefs.timezoneMode.set('panchanga_place');
    prefs.setPanchangaPlace({ city: 'Singapore', nation: 'SG', timezone: 'Asia/Singapore', label: 'Singapore' } as any);
    await service.calendarIntelligence('profile-1', 45);

    expect(service.cachedCalendarIntelligence('profile-1', 45)).not.toBeNull();
    expect(service.cachedCalendarIntelligence('profile-1', 45, undefined, { includePractitionerDetail: true })).toBeNull();

    prefs.setPanchangaPlace({ city: 'Chennai', nation: 'IN', timezone: 'Asia/Kolkata', label: 'Chennai' } as any);
    expect(service.cachedCalendarIntelligence('profile-1', 45)).toBeNull();
  });

  it('does not resurrect hard-expired Calendar data from a suspended WebView memory cache', async () => {
    const clock = spyOn(Date, 'now').and.returnValue(1_000);
    await service.calendarIntelligence('profile-1', 45);

    clock.and.returnValue(1_000 + (46 * 24 * 60 * 60 * 1000));

    expect(service.cachedCalendarIntelligenceEntry('profile-1', 45)).toBeNull();
    await service.calendarIntelligence('profile-1', 45);
    expect(api.get).toHaveBeenCalledTimes(2);
  });

  it('does not restore Today cache when an in-flight refresh completes after logout cleanup', async () => {
    let resolve!: (value: any) => void;
    api.get.and.returnValue(new Promise((done) => { resolve = done; }));

    const refresh = service.refreshDailyGuidance('profile-1');
    service.clearConfiguredProfiles();
    resolve({ date: '2026-08-14' });
    await refresh;

    service.configureProfile({ id: 'profile-1', user_id: 'user-1', updated_at: '2026-08-11T00:00:00Z' });
    expect(service.cachedDailyGuidanceEntry('profile-1')).toBeNull();
    expect(Object.keys(localStorage).some((key) => key.startsWith('siddha.resource-cache'))).toBeFalse();
  });

  it('does not restore Calendar cache when an in-flight refresh completes after logout cleanup', async () => {
    let resolve!: (value: any) => void;
    api.get.and.returnValue(new Promise((done) => { resolve = done; }));

    const refresh = service.refreshCalendarIntelligence('profile-1', 45);
    service.clearConfiguredProfiles();
    resolve({ panchanga_days: [], by_date: {} });
    await refresh;

    service.configureProfile({ id: 'profile-1', user_id: 'user-1', updated_at: '2026-08-11T00:00:00Z' });
    expect(service.cachedCalendarIntelligenceEntry('profile-1', 45)).toBeNull();
    expect(Object.keys(localStorage).some((key) => key.startsWith('siddha.resource-cache'))).toBeFalse();
  });
});
