import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, UrlTree } from '@angular/router';

import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';
import { mobileAuthGuard } from './mobile-auth.guard';

describe('mobileAuthGuard', () => {
  const originalProduction = environment.production;
  let auth: { init: jasmine.Spy; isAuthenticated: jasmine.Spy; session: ReturnType<typeof signal<unknown>> };
  let router: jasmine.SpyObj<Router>;
  const signInTree = {} as UrlTree;

  beforeEach(() => {
    environment.production = true;
    auth = {
      init: jasmine.createSpy('init'),
      isAuthenticated: jasmine.createSpy('isAuthenticated'),
      session: signal<unknown>(null),
    };
    router = jasmine.createSpyObj<Router>('Router', ['createUrlTree']);
    router.createUrlTree.and.returnValue(signInTree);
    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: auth },
        { provide: Router, useValue: router },
      ],
    });
  });

  afterEach(() => { environment.production = originalProduction; });

  function run() {
    return TestBed.runInInjectionContext(() => mobileAuthGuard({} as never, {} as never));
  }

  it('lets a restored session through when init fails offline', async () => {
    auth.init.and.rejectWith(new TypeError('Failed to fetch'));
    auth.session.set({ access_token: 'stale' });
    expect(await run()).toBeTrue();
  });

  it('sends a first launch with no network to sign-in', async () => {
    auth.init.and.rejectWith(new TypeError('Failed to fetch'));
    expect(await run()).toBe(signInTree);
    expect(router.createUrlTree).toHaveBeenCalledWith(['/m', 'auth']);
  });

  it('keeps the normal online path', async () => {
    auth.init.and.resolveTo(undefined);
    auth.isAuthenticated.and.returnValue(false);
    expect(await run()).toBe(signInTree);
    auth.isAuthenticated.and.returnValue(true);
    expect(await run()).toBeTrue();
  });
});
