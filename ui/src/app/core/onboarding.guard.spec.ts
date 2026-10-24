import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, UrlTree } from '@angular/router';

import { AuthService } from './auth.service';
import { KundliStore } from './kundli.store';
import { onboardedRedirectGuard } from './onboarding.guard';

describe('onboardedRedirectGuard', () => {
  let auth: {
    init: jasmine.Spy;
    isAuthenticated: jasmine.Spy;
    enabled: ReturnType<typeof signal<boolean>>;
    signedOut: ReturnType<typeof signal<boolean>>;
    session: ReturnType<typeof signal<unknown>>;
  };
  let kundlis: { load: jasmine.Spy; kundlis: ReturnType<typeof signal<{ relation?: string }[]>> };
  let router: jasmine.SpyObj<Router>;
  const todayTree = {} as UrlTree;

  beforeEach(() => {
    auth = {
      init: jasmine.createSpy('init').and.resolveTo(undefined),
      isAuthenticated: jasmine.createSpy('isAuthenticated').and.returnValue(true),
      enabled: signal(true),
      signedOut: signal(false),
      session: signal<unknown>({ access_token: 'token' }),
    };
    kundlis = { load: jasmine.createSpy('load').and.resolveTo(undefined), kundlis: signal([]) };
    router = jasmine.createSpyObj<Router>('Router', ['createUrlTree']);
    router.createUrlTree.and.returnValue(todayTree);
    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: auth },
        { provide: KundliStore, useValue: kundlis },
        { provide: Router, useValue: router },
      ],
    });
  });

  function run(path: string) {
    const route = { routeConfig: { path } } as ActivatedRouteSnapshot;
    return TestBed.runInInjectionContext(() => onboardedRedirectGuard(route, {} as never));
  }

  it('sends an onboarded reader from the entry screen to Today', async () => {
    kundlis.kundlis.set([{ relation: 'self' }]);
    expect(await run('m/start')).toBe(todayTree);
    expect(router.createUrlTree).toHaveBeenCalledWith(['/m', 'today']);
  });

  it('lets a signed-in reader with no self profile continue onboarding', async () => {
    expect(await run('m/start')).toBeTrue();
  });

  it('shows the welcome screen to a signed-out reader', async () => {
    auth.isAuthenticated.and.returnValue(false);
    auth.session.set(null);
    expect(await run('m/start')).toBeTrue();
    expect(kundlis.load).not.toHaveBeenCalled();
  });

  it('does not show the welcome screen to a signed-in reader whose profiles failed to load', async () => {
    kundlis.load.and.rejectWith(new Error('That took too long to answer.'));
    expect(await run('m/start')).toBe(todayTree);
    expect(router.createUrlTree).toHaveBeenCalledWith(['/m', 'today']);
  });

  it('keeps a failed load on later onboarding steps where it was', async () => {
    kundlis.load.and.rejectWith(new Error('That took too long to answer.'));
    expect(await run('m/birth-details')).toBeTrue();
  });

  it('sends a restored session to Today when auth cannot initialise', async () => {
    auth.init.and.rejectWith(new TypeError('Failed to fetch'));
    expect(await run('m/start')).toBe(todayTree);
    auth.session.set(null);
    expect(await run('m/start')).toBeTrue();
  });
});
