import { TestBed } from '@angular/core/testing';

import { ApiService } from './api.service';
import { EntitlementService } from './entitlement.service';
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
      engine_version: 'daily-guidance-1.1',
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

  it('requests and caches a bounded selected-day payload independently from the month', async () => {
    prefs.timezoneMode.set('panchanga_place');
    prefs.setPanchangaPlace({ city: 'Singapore', nation: 'SG', timezone: 'Asia/Singapore', label: 'Singapore' } as any);

    await service.calendarIntelligence('profile-1', 1, undefined, {
      includePractitionerDetail: true,
      asOf: '2026-09-03',
    });

    const path = api.get.calls.mostRecent().args[0] as string;
    expect(path).toContain('days=1');
    expect(path).toContain('as_of=2026-09-03');
    expect(path).toContain('include_practitioner_detail=true');
    expect(path).toContain('timezone=Asia%2FSingapore');
    expect(service.cachedCalendarIntelligenceEntry('profile-1', 1, undefined, {
      includePractitionerDetail: true,
      asOf: '2026-09-03',
    })).not.toBeNull();
    expect(service.cachedCalendarIntelligenceEntry('profile-1', 1, undefined, {
      includePractitionerDetail: true,
      asOf: '2026-09-04',
    })).toBeNull();
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

describe('VedicService agent daily brief', () => {
  let api: jasmine.SpyObj<ApiService>;
  let service: VedicService;

  beforeEach(() => {
    localStorage.clear();
    api = jasmine.createSpyObj<ApiService>('ApiService', ['get', 'put']);
    TestBed.configureTestingModule({
      providers: [VedicService, PreferencesService, { provide: ApiService, useValue: api }],
    });
    service = TestBed.inject(VedicService);
  });

  it('asks for the reading style and keeps a written brief for the session', async () => {
    api.get.and.resolveTo({ date: '2026-10-16', source: 'agent', brief: { headline: 'h' } } as any);
    await service.dailyBrief('profile-1', '2026-10-16', 'gentle', 'guided');
    await service.dailyBrief('profile-1', '2026-10-16', 'gentle', 'guided');
    expect(api.get).toHaveBeenCalledTimes(1);
    expect(api.get.calls.mostRecent().args[0]).toContain('/context/profile-1/daily/brief?');
    expect(api.get.calls.mostRecent().args[0]).toContain('tone=gentle');
    expect(api.get.calls.mostRecent().args[0]).toContain('mode=guided');

    await service.dailyBrief('profile-1', '2026-10-16', 'direct', 'guided');
    expect(api.get).toHaveBeenCalledTimes(2);
  });

  it('asks again after a template answer or an error', async () => {
    api.get.and.resolveTo({ date: '2026-10-16', source: 'template', brief: null } as any);
    await service.dailyBrief('profile-1', '2026-10-16', 'direct', 'balanced');
    api.get.and.rejectWith(new Error('offline'));
    await expectAsync(service.dailyBrief('profile-1', '2026-10-16', 'direct', 'balanced')).toBeRejected();
    api.get.and.resolveTo({ date: '2026-10-16', source: 'agent', brief: { headline: 'h' } } as any);
    const answer = await service.dailyBrief('profile-1', '2026-10-16', 'direct', 'balanced');
    expect(answer.source).toBe('agent');
    expect(api.get).toHaveBeenCalledTimes(3);
  });

  it('keeps a written brief on the device, so a relaunch shows it at once', async () => {
    api.get.and.resolveTo({ date: '2026-10-16', source: 'agent', brief: { headline: 'h' } } as any);
    await service.dailyBrief('profile-1', '2026-10-16', 'gentle', 'balanced');
    const relaunched = TestBed.runInInjectionContext(() => new VedicService());
    const answer = await relaunched.dailyBrief('profile-1', '2026-10-16', 'gentle', 'balanced');
    // Shown from the device at once; one background check for a newer brief.
    expect(answer.brief?.headline).toBe('h');
    expect(api.get).toHaveBeenCalledTimes(2);
    await relaunched.dailyBrief('profile-1', '2026-10-16', 'gentle', 'balanced');
    expect(api.get).toHaveBeenCalledTimes(2);
    // The next Vedic day is a new brief.
    await relaunched.dailyBrief('profile-1', '2026-10-17', 'gentle', 'balanced');
    expect(api.get).toHaveBeenCalledTimes(3);
  });

  it('shows a stored brief at once and swaps in a newer one from the server', async () => {
    api.get.and.resolveTo({ date: '2026-10-16', source: 'agent', generated_at: 'a', brief: { headline: 'old' } } as any);
    await service.dailyBrief('profile-1', '2026-10-16', 'gentle', 'balanced');
    api.get.and.resolveTo({ date: '2026-10-16', source: 'agent', generated_at: 'b', brief: { headline: 'new' } } as any);
    const relaunched = TestBed.runInInjectionContext(() => new VedicService());
    let fresh: any = null;
    const shown = await relaunched.dailyBrief('profile-1', '2026-10-16', 'gentle', 'balanced', (value) => (fresh = value));
    expect(shown.brief?.headline).toBe('old');
    await new Promise((resolve) => setTimeout(resolve));
    expect(fresh?.brief?.headline).toBe('new');
    const later = TestBed.runInInjectionContext(() => new VedicService());
    expect((await later.dailyBrief('profile-1', '2026-10-16', 'gentle', 'balanced')).brief?.headline).toBe('new');
  });
});

describe('VedicService plan-shaped caches', () => {
  let api: jasmine.SpyObj<ApiService>;
  let service: VedicService;
  let entitlements: EntitlementService;

  const snapshot = (enforced: boolean, plus: boolean) => ({
    quotas_enforced: enforced,
    entitlements: { 'vargas.full': false, 'yogas.full': plus, 'remedies.full': plus },
  }) as any;

  beforeEach(() => {
    localStorage.clear();
    api = jasmine.createSpyObj<ApiService>('ApiService', ['get', 'put']);
    api.get.and.resolveTo({ groups: [] } as any);
    TestBed.configureTestingModule({
      providers: [VedicService, PreferencesService, { provide: ApiService, useValue: api }],
    });
    service = TestBed.inject(VedicService);
    entitlements = TestBed.inject(EntitlementService);
  });

  it('refetches a trimmed remedy plan once the plan opens it', async () => {
    entitlements.current.set(snapshot(true, false));
    TestBed.tick();
    await service.remedyPlan('profile-1');
    await service.remedyPlan('profile-1');
    expect(api.get).toHaveBeenCalledTimes(1);

    entitlements.current.set(snapshot(true, true));
    TestBed.tick();
    await service.remedyPlan('profile-1');
    expect(api.get).toHaveBeenCalledTimes(2);
  });

  it('keeps the cache when only the snapshot is refreshed', async () => {
    entitlements.current.set(snapshot(false, false));
    TestBed.tick();
    await service.remedyPlan('profile-1');
    entitlements.current.set(snapshot(false, true));
    TestBed.tick();
    await service.remedyPlan('profile-1');
    expect(api.get).toHaveBeenCalledTimes(1);
  });
});
