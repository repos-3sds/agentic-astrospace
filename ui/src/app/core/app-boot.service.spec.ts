import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';

import { AppBootService } from './app-boot.service';
import { AuthService } from './auth.service';
import { KundliStore } from './kundli.store';
import { PreferencesService } from './preferences.service';
import { PanchangAlarmService } from './panchang-alarm.service';
import { PushService } from './push.service';

describe('AppBootService', () => {
  let auth: { init: jasmine.Spy; isAuthenticated: () => boolean; enabled: () => boolean; session: () => unknown };
  let store: jasmine.SpyObj<KundliStore>;
  let prefs: jasmine.SpyObj<PreferencesService>;

  beforeEach(() => {
    auth = {
      init: jasmine.createSpy('init').and.resolveTo(),
      isAuthenticated: () => true,
      enabled: () => true,
      session: () => ({ access_token: 't' }),
    };
    store = jasmine.createSpyObj<KundliStore>('KundliStore', ['load']);
    store.load.and.resolveTo();
    prefs = jasmine.createSpyObj<PreferencesService>('PreferencesService', ['syncCloud']);
    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: auth },
        { provide: KundliStore, useValue: store },
        { provide: PreferencesService, useValue: prefs },
        { provide: PushService, useValue: { init: () => Promise.resolve() } },
        { provide: PanchangAlarmService, useValue: { init: () => Promise.resolve() } },
        { provide: Router, useValue: { url: '/m/today', navigateByUrl: () => Promise.resolve(true) } },
      ],
    });
  });

  it('does not hold first render on the /settings sync', async () => {
    // A sync that never answers (a stalled network) must not stall boot.
    prefs.syncCloud.and.returnValue(new Promise<void>(() => undefined));

    await TestBed.inject(AppBootService).run();

    expect(prefs.syncCloud).toHaveBeenCalled();
    expect(store.load).toHaveBeenCalled();
  });

  it('reports a failed boot instead of throwing, so the splash still lifts', async () => {
    auth.init.and.rejectWith(new Error('Could not load auth configuration'));
    const boot = TestBed.inject(AppBootService);

    await expectAsync(boot.run()).toBeResolved();

    expect(boot.error()).toBe('Could not load auth configuration');
    expect(store.load).not.toHaveBeenCalled();
  });

  it('skips the profile load for a signed-out launch', async () => {
    auth.isAuthenticated = () => false;
    const boot = TestBed.inject(AppBootService);

    await boot.run();

    expect(store.load).not.toHaveBeenCalled();
    expect(boot.error()).toBeNull();
  });
});

