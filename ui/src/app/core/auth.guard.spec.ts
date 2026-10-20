import { TestBed } from '@angular/core/testing';
import { Router, UrlTree } from '@angular/router';

import { environment } from '../../environments/environment';
import { AdminService } from './admin.service';
import { AuthService } from './auth.service';
import { authGuard } from './auth.guard';

describe('authGuard', () => {
  const originalProduction = environment.production;
  let auth: { init: jasmine.Spy; isAuthenticated: jasmine.Spy };
  let admin: { me: jasmine.Spy };
  let router: jasmine.SpyObj<Router>;
  const signInTree = {} as UrlTree;
  const landingTree = {} as UrlTree;

  beforeEach(() => {
    environment.production = true;
    auth = {
      init: jasmine.createSpy('init').and.resolveTo(undefined),
      isAuthenticated: jasmine.createSpy('isAuthenticated').and.returnValue(true),
    };
    admin = { me: jasmine.createSpy('me') };
    router = jasmine.createSpyObj<Router>('Router', ['createUrlTree']);
    router.createUrlTree.and.callFake((commands: unknown[]) =>
      commands[0] === '/auth' ? signInTree : landingTree,
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

  it('sends any other signed-in web user to the landing page', async () => {
    admin.me.and.rejectWith(new Error('403'));
    expect(await run()).toBe(landingTree);
    // Flagged, so the landing page says why instead of looking like a dead button.
    expect(router.createUrlTree).toHaveBeenCalledWith(['/'], { queryParams: { owner_only: '1' } });
  });

  it('keeps development builds open', async () => {
    environment.production = false;
    expect(await run()).toBeTrue();
    expect(admin.me).not.toHaveBeenCalled();
  });
});
