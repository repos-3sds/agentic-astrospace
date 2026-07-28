import { Capacitor } from '@capacitor/core';
import { Router } from '@angular/router';

import { AuthService } from './auth.service';

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
    service = new AuthService(router);

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

  function stateFrom(redirectUrl: string): string {
    return new URL(redirectUrl).searchParams.get('state')!;
  }

  it('accepts a fragment-token callback that carries the state this app issued', async () => {
    const state = stateFrom(issueCallbackUrl('/m/today'));

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
    const state = stateFrom(issueCallbackUrl());
    const url = `${CALLBACK_BASE}?state=${state}#access_token=abc&refresh_token=def`;

    await (service as any).handleNativeAuthCallback(url);
    expect(client.auth.setSession).toHaveBeenCalledTimes(1);

    await expectAsync((service as any).handleNativeAuthCallback(url)).toBeRejectedWithError(
      /could not be verified/,
    );
    expect(client.auth.setSession).toHaveBeenCalledTimes(1); // still just the first call
  });

  it('rejects a state that has passed its TTL', async () => {
    const state = stateFrom(issueCallbackUrl());
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
