import { TestBed } from '@angular/core/testing';
import { Router, UrlTree } from '@angular/router';

import { environment } from '../../environments/environment';
import { AdminService } from './admin.service';
import { AuthService } from './auth.service';
import { authGuard, publicSite, webLandingGuard } from './auth.guard';

describe('authGuard', () => {
  const originalProduction = environment.production;
  let auth: { init: jasmine.Spy; isAuthenticated: jasmine.Spy; signOut: jasmine.Spy };
  let admin: { me: jasmine.Spy };
  let router: jasmine.SpyObj<Router>;
  const signInTree = {} as UrlTree;
  const landingTree = {} as UrlTree;
  const appTree = {} as UrlTree;

  beforeEach(() => {
    environment.production = true;
    auth = {
      init: jasmine.createSpy('init').and.resolveTo(undefined),
      isAuthenticated: jasmine.createSpy('isAuthenticated').and.returnValue(true),
      signOut: jasmine.createSpy('signOut').and.resolveTo(undefined),
    };
    admin = { me: jasmine.createSpy('me') };
    router = jasmine.createSpyObj<Router>('Router', ['createUrlTree']);
    router.createUrlTree.and.callFake((commands: unknown[]) =>
      commands[0] === '/auth' ? signInTree : commands[0] === '/app' ? appTree : landingTree,
    );
    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: auth },
        { provide: AdminService, useValue: admin },
        { provide: Router, useValue: router },
      ],
    });
  });

  afterEach(() => { environment.production = originalProduction; });

  function run() {
    return TestBed.runInInjectionContext(() => authGuard({} as never, {} as never));
  }

  it('sends a signed-out visitor to sign-in', async () => {
    auth.isAuthenticated.and.returnValue(false);
    expect(await run()).toBe(signInTree);
    expect(admin.me).not.toHaveBeenCalled();
  });

  it('lets the owner into the production web app', async () => {
    admin.me.and.resolveTo({ id: 'u', email: 'owner@example.com', role: 'admin' });
    expect(await run()).toBeTrue();
  });

  it('signs any other web user out and tells them the app is the way in', async () => {
    admin.me.and.rejectWith(new Error('403'));
    expect(await run()).toBe(signInTree);
    expect(auth.signOut).toHaveBeenCalled();
    expect(router.createUrlTree).toHaveBeenCalledWith(['/auth'], { queryParams: { owner_only: '1' } });
  });

  it('keeps development builds open', async () => {
    environment.production = false;
    expect(await run()).toBeTrue();
    expect(admin.me).not.toHaveBeenCalled();
  });

  describe('web landing', () => {
    let go: jasmine.Spy;
    beforeEach(() => { go = spyOn(publicSite, 'go'); });

    function land() {
      return TestBed.runInInjectionContext(() => webLandingGuard({} as never, {} as never));
    }

    it('sends a visitor to asksiddha.app instead of showing the web app', async () => {
      auth.isAuthenticated.and.returnValue(false);
      expect(await land()).toBeFalse();
      expect(go).toHaveBeenCalledWith('https://asksiddha.app/');
    });

    it('signs out a non-owner and sends them to asksiddha.app', async () => {
      admin.me.and.rejectWith(new Error('403'));
      expect(await land()).toBeFalse();
      expect(auth.signOut).toHaveBeenCalled();
      expect(go).toHaveBeenCalled();
    });

    it('takes the owner straight into the web app', async () => {
      admin.me.and.resolveTo({ id: 'u', email: 'owner@example.com', role: 'admin' });
      expect(await land()).toBe(appTree);
      expect(go).not.toHaveBeenCalled();
    });

    it('keeps the landing page in development builds', async () => {
      environment.production = false;
      expect(await land()).toBeTrue();
      expect(go).not.toHaveBeenCalled();
    });
  });
});
