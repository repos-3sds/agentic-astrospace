import { Capacitor } from '@capacitor/core';
import { Router } from '@angular/router';
import { Session } from '@supabase/supabase-js';

import { AuthService } from './auth.service';
import { ConnectivityService } from './connectivity.service';

function connectivitySpy(): jasmine.SpyObj<ConnectivityService> {
  return jasmine.createSpyObj<ConnectivityService>('ConnectivityService', [
    'noteRequestSuccess',
    'noteRequestFailure',
  ]);
}

/**
 * The native OAuth/magic-link/password-reset callback arrives over a custom
 * URL scheme (`app.astrospace.mobile://auth/callback`) that's registered
 * BROWSABLE with autoVerify off — reachable from any other installed app or
 * a tapped web link, not just the email Supabase actually sent. The `code`
 * branch is already safe: exchanging a PKCE code for a session requires the
 * verifier this app instance generated, so an intercepted code is inert.
 * The `access_token`/`refresh_token` fragment branch had no equivalent
 * protection — accepting it directly would let anyone who can fire the
 * scheme hand this app a session for an account they control. These tests
 * exercise the state/nonce gate added to close that: legitimate callbacks
 * still work, forged ones no longer establish a session.
 */
describe('AuthService native auth callback', () => {
  const STATE_KEY = 'astrospace.nativeAuthState';
  const DESTINATION_KEY = 'astrospace.nativeAuthDestination';
  const CALLBACK_BASE = 'app.astrospace.mobile://auth/callback';

  let service: AuthService;
  let client: {
    auth: {
      exchangeCodeForSession: jasmine.Spy;
      setSession: jasmine.Spy;
      onAuthStateChange: jasmine.Spy;
    };
  };
  let router: jasmine.SpyObj<Router>;
  const fakeSession = { access_token: 'live-token', user: { id: 'u1' } } as any;

  beforeEach(() => {
    spyOn(Capacitor, 'isNativePlatform').and.returnValue(true);
    localStorage.removeItem(STATE_KEY);
    localStorage.removeItem(DESTINATION_KEY);

    router = jasmine.createSpyObj<Router>('Router', ['navigate', 'navigateByUrl']);
    service = new AuthService(router, connectivitySpy());

    client = {
      auth: {
        exchangeCodeForSession: jasmine
          .createSpy('exchangeCodeForSession')
          .and.resolveTo({ data: { session: fakeSession }, error: null }),
        setSession: jasmine
          .createSpy('setSession')
          .and.resolveTo({ data: { session: fakeSession }, error: null }),
        onAuthStateChange: jasmine.createSpy('onAuthStateChange'),
      },
    };
    (service as any).client = client;
  });

  afterEach(() => {
    localStorage.removeItem(STATE_KEY);
    localStorage.removeItem(DESTINATION_KEY);
  });

  /** Mirrors what signInWithMagicLink/resetPassword/signInWithGoogle do. */
  function issueCallbackUrl(destination = '/m/today'): string {
    const redirect: string = (service as any).authRedirect(destination);
    return redirect;
  }

  function storedState(): string {
    return JSON.parse(localStorage.getItem(STATE_KEY)!)?.nonce;
  }

  it('accepts a fragment-token callback that carries the state this app issued', async () => {
    issueCallbackUrl('/m/today');
    const state = storedState();

    await (service as any).handleNativeAuthCallback(
      `${CALLBACK_BASE}?state=${state}#access_token=abc&refresh_token=def`,
    );

    expect(client.auth.setSession).toHaveBeenCalledWith({
      access_token: 'abc',
      refresh_token: 'def',
    });
    expect(service.session()).toBe(fakeSession);
    expect(router.navigateByUrl).toHaveBeenCalledWith('/m/today');
  });

  it('accepts a code-exchange callback regardless of state — already PKCE-protected', async () => {
    // Deliberately not gated: exchanging a code requires the verifier this
    // app instance holds, so this branch doesn't need the state check the
    // fragment branch relies on. No authRedirect call precedes this at all.
    await (service as any).handleNativeAuthCallback(`${CALLBACK_BASE}?code=xyz`);

    expect(client.auth.exchangeCodeForSession).toHaveBeenCalledWith('xyz');
    expect(service.session()).toBe(fakeSession);
  });

  it('keeps the native redirect URL fixed so Supabase allow-list matching is stable', () => {
    expect(issueCallbackUrl('/m/today')).toContain(CALLBACK_BASE);
    expect(localStorage.getItem(DESTINATION_KEY)).toBe('/m/today');
    expect(storedState()).toBeTruthy();
  });

  it('rejects a callback with no state parameter at all', async () => {
    issueCallbackUrl(); // a real flow is in flight, but the callback omits state entirely

    await expectAsync(
      (service as any).handleNativeAuthCallback(
        `${CALLBACK_BASE}#access_token=abc&refresh_token=def`,
      ),
    ).toBeRejectedWithError(/could not be verified/);

    expect(client.auth.setSession).not.toHaveBeenCalled();
    expect(service.session()).toBeNull();
  });

  it('rejects a callback whose state does not match what was issued', async () => {
    issueCallbackUrl(); // attacker doesn't know this value

    await expectAsync(
      (service as any).handleNativeAuthCallback(
        `${CALLBACK_BASE}?state=forged-by-attacker#access_token=abc&refresh_token=def`,
      ),
    ).toBeRejectedWithError(/could not be verified/);

    expect(client.auth.setSession).not.toHaveBeenCalled();
  });

  it('rejects a callback when no flow was ever started (no state on record)', async () => {
    // Nothing called authRedirect — this is the exact shape of the original
    // bypass: a URL fired at the app with tokens but no local flow at all.
    await expectAsync(
      (service as any).handleNativeAuthCallback(
        `${CALLBACK_BASE}#access_token=abc&refresh_token=def`,
      ),
    ).toBeRejectedWithError(/could not be verified/);

    expect(client.auth.setSession).not.toHaveBeenCalled();
  });

  it('is single-use: replaying an already-consumed state is rejected', async () => {
    issueCallbackUrl();
    const state = storedState();
    const url = `${CALLBACK_BASE}?state=${state}#access_token=abc&refresh_token=def`;

    await (service as any).handleNativeAuthCallback(url);
    expect(client.auth.setSession).toHaveBeenCalledTimes(1);

    await expectAsync((service as any).handleNativeAuthCallback(url)).toBeRejectedWithError(
      /could not be verified/,
    );
    expect(client.auth.setSession).toHaveBeenCalledTimes(1); // still just the first call
  });

  it('rejects a state that has passed its TTL', async () => {
    issueCallbackUrl();
    const state = storedState();
    const stored = JSON.parse(localStorage.getItem(STATE_KEY)!);
    stored.issuedAt = Date.now() - 11 * 60 * 1000; // 11 minutes ago, TTL is 10
    localStorage.setItem(STATE_KEY, JSON.stringify(stored));

    await expectAsync(
      (service as any).handleNativeAuthCallback(
        `${CALLBACK_BASE}?state=${state}#access_token=abc&refresh_token=def`,
      ),
    ).toBeRejectedWithError(/could not be verified/);

    expect(client.auth.setSession).not.toHaveBeenCalled();
  });
});

describe('AuthService access-token resilience', () => {
  let service: AuthService;
  let router: jasmine.SpyObj<Router>;

  beforeEach(() => {
    router = jasmine.createSpyObj<Router>('Router', ['navigate', 'navigateByUrl']);
    service = new AuthService(router, connectivitySpy());
    service.enabled.set(true);
    (service as any).initPromise = Promise.resolve();
  });

  it('keeps a still-valid session when Supabase has a transient getSession error', async () => {
    const session = {
      access_token: 'cached-live-token',
      expires_at: Math.floor(Date.now() / 1000) + 300,
      user: { id: 'u1' },
    } as Session;
    (service as any).setSession(session);
    (service as any).client = {
      auth: {
        getSession: jasmine.createSpy('getSession').and.resolveTo({
          data: { session: null },
          error: new Error('Failed to fetch'),
        }),
      },
    };

    await expectAsync(service.getAccessToken()).toBeResolvedTo('cached-live-token');
    expect(service.session()).toBe(session);
    expect(service.isAuthenticated()).toBeTrue();
  });

  it('does not send an expired token after a refresh error, but preserves route auth state', async () => {
    const session = {
      access_token: 'expired-token',
      expires_at: Math.floor(Date.now() / 1000) - 10,
      user: { id: 'u1' },
    } as Session;
    (service as any).setSession(session);
    (service as any).client = {
      auth: {
        getSession: jasmine.createSpy('getSession').and.resolveTo({
          data: { session: null },
          error: new Error('Failed to fetch'),
        }),
      },
    };

    await expectAsync(service.getAccessToken()).toBeResolvedTo(null);
    expect(service.session()).toBe(session);
    expect(service.isAuthenticated()).toBeTrue();
  });
});
