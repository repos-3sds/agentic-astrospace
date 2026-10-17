import { Capacitor } from '@capacitor/core';
import { Router } from '@angular/router';
import { Session } from '@supabase/supabase-js';

import { Preferences } from '@capacitor/preferences';
import { ResourceCacheService } from './resource-cache.service';

import { AuthService } from './auth.service';
import { ConnectivityService } from './connectivity.service';

function connectivitySpy(): jasmine.SpyObj<ConnectivityService> {
  return jasmine.createSpyObj<ConnectivityService>('ConnectivityService', [
    'noteRequestSuccess',
    'noteRequestFailure',
  ]);
}

function cacheSpy(): ResourceCacheService {
  return jasmine.createSpyObj<ResourceCacheService>('ResourceCacheService', ['clearAll']);
}

/**
 * The native OAuth/magic-link/password-reset callback arrives over a custom
 * URL scheme (`app.asksiddha.mobile://auth/callback`) that's registered
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
  const CALLBACK_BASE = 'app.asksiddha.mobile://auth/callback';

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
    service = new AuthService(router, connectivitySpy(), cacheSpy());

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
    service = new AuthService(router, connectivitySpy(), cacheSpy());
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


/**
 * Offline relaunch. Until 2026-10-15 a failed /auth/config fetch rethrew and
 * the mobile auth guard awaited it, so a returning user with no network was
 * sent to sign-in even though their guidance was cached on device.
 */
describe('AuthService offline relaunch', () => {
  const CONFIG_KEY = 'astrospace.authConfig';
  const SUPABASE_URL = 'https://abcproject.supabase.co';
  const SESSION_KEY = 'sb-abcproject-auth-token';
  const config = { enabled: true, supabase_url: SUPABASE_URL, supabase_anon_key: 'anon' };
  const storedSession = { access_token: 'stale-token', refresh_token: 'r', expires_at: 1, user: { id: 'u1', email: 'a@b.c' } };

  let service: AuthService;
  let router: jasmine.SpyObj<Router>;
  let getSession: jasmine.Spy;

  beforeEach(async () => {
    await Preferences.clear();
    router = jasmine.createSpyObj<Router>('Router', ['navigate', 'navigateByUrl']);
    service = new AuthService(router, connectivitySpy(), cacheSpy());
    getSession = jasmine.createSpy('getSession');
    spyOn(service as any, 'buildClient').and.returnValue({
      auth: { getSession, onAuthStateChange: jasmine.createSpy('onAuthStateChange') },
    });
  });

  afterEach(async () => { await Preferences.clear(); });

  it('caches the auth config after a successful fetch', async () => {
    spyOn(window, 'fetch').and.resolveTo(new Response(JSON.stringify(config), { status: 200 }));
    getSession.and.resolveTo({ data: { session: storedSession }, error: null });

    await service.init();

    expect((await Preferences.get({ key: CONFIG_KEY })).value).toBe(JSON.stringify(config));
    expect(service.ready()).toBeTrue();
    expect(service.session()?.access_token).toBe('stale-token');
  });

  it('relaunches on the cached config and stored session when the network is down', async () => {
    await Preferences.set({ key: CONFIG_KEY, value: JSON.stringify(config) });
    await Preferences.set({ key: SESSION_KEY, value: JSON.stringify(storedSession) });
    spyOn(window, 'fetch').and.rejectWith(new TypeError('Failed to fetch'));
    // supabase-js cannot refresh offline and reports that as an error.
    getSession.and.resolveTo({ data: { session: null }, error: new Error('AuthRetryableFetchError') });

    await service.init();

    expect(service.ready()).toBeTrue();
    expect(service.enabled()).toBeTrue();
    expect(service.session()?.user?.id).toBe('u1');
    expect(service.isAuthenticated()).toBeTrue();
  });

  it('stays signed in when supabase-js then reports the failed offline refresh as a null initial session', async () => {
    await Preferences.set({ key: CONFIG_KEY, value: JSON.stringify(config) });
    await Preferences.set({ key: SESSION_KEY, value: JSON.stringify(storedSession) });
    spyOn(window, 'fetch').and.rejectWith(new TypeError('Failed to fetch'));
    getSession.and.resolveTo({ data: { session: null }, error: new Error('AuthRetryableFetchError') });
    const listen = (service as any).buildClient().auth.onAuthStateChange as jasmine.Spy;

    await service.init();
    const callback = listen.calls.mostRecent().args[0];
    callback('INITIAL_SESSION', null);
    expect(service.session()?.user?.id).toBe('u1');

    callback('SIGNED_OUT', null);
    expect(service.session()).toBeNull();
  });

  it('boots from the cached config without waiting on the network, and revalidates it behind', async () => {
    const rotated = { ...config, supabase_anon_key: 'rotated' };
    await Preferences.set({ key: CONFIG_KEY, value: JSON.stringify(config) });
    let answer!: (response: Response) => void;
    spyOn(window, 'fetch').and.returnValue(new Promise<Response>((resolve) => (answer = resolve)));
    getSession.and.resolveTo({ data: { session: storedSession }, error: null });

    // The config request has not answered, and boot is already done.
    await service.init();
    expect(service.ready()).toBeTrue();
    expect((service as any).buildClient).toHaveBeenCalledWith(SUPABASE_URL, 'anon');

    answer(new Response(JSON.stringify(rotated), { status: 200 }));
    let stored: string | null = null;
    for (let i = 0; i < 50 && stored !== JSON.stringify(rotated); i++) {
      await new Promise((resolve) => setTimeout(resolve, 10));
      stored = (await Preferences.get({ key: CONFIG_KEY })).value;
    }
    // Stored for the next launch; this one keeps the client it built.
    expect(stored).toBe(JSON.stringify(rotated));
  });

  it('does not let a stalled session refresh hold boot: the stored session stands in', async () => {
    jasmine.clock().install();
    try {
      await Preferences.set({ key: CONFIG_KEY, value: JSON.stringify(config) });
      await Preferences.set({ key: SESSION_KEY, value: JSON.stringify(storedSession) });
      spyOn(window, 'fetch').and.returnValue(new Promise<Response>(() => undefined));
      getSession.and.returnValue(new Promise(() => undefined));

      let done = false;
      const booted = service.init().then(() => (done = true));
      // Advance a second at a time, letting the async storage reads settle in
      // between, until boot gives up on the refresh (bounded at 8 s).
      let elapsed = 0;
      while (!done && elapsed < 20_000) {
        for (let i = 0; i < 10; i++) await Promise.resolve();
        jasmine.clock().tick(1_000);
        elapsed += 1_000;
      }
      await booted;
      expect(elapsed).toBeLessThanOrEqual(9_000);

      expect(service.session()?.user?.id).toBe('u1');
      expect(service.isAuthenticated()).toBeTrue();
    } finally {
      jasmine.clock().uninstall();
    }
  });

  it('still fails on a first launch with no network and nothing cached', async () => {
    spyOn(window, 'fetch').and.rejectWith(new TypeError('Failed to fetch'));

    await expectAsync(service.init()).toBeRejected();
    expect(service.ready()).toBeFalse();
    expect(getSession).not.toHaveBeenCalled();
  });

  it('does not resurrect a session after a real sign-out', async () => {
    await Preferences.set({ key: CONFIG_KEY, value: JSON.stringify(config) });
    spyOn(window, 'fetch').and.rejectWith(new TypeError('Failed to fetch'));
    getSession.and.resolveTo({ data: { session: null }, error: new Error('offline') });

    await expectAsync(service.init()).toBeRejected();
    expect(service.session()).toBeNull();
  });

  it('wipes the encrypted cache on sign-out so the next account starts clean', async () => {
    spyOn(window, 'fetch').and.resolveTo(new Response(JSON.stringify(config), { status: 200 }));
    getSession.and.resolveTo({ data: { session: storedSession }, error: null });
    const signOut = jasmine.createSpy('signOut').and.resolveTo({ error: null });
    (service as any).buildClient.and.returnValue({
      auth: { getSession, signOut, onAuthStateChange: jasmine.createSpy('onAuthStateChange') },
    });
    await service.init();

    await service.signOut(['/m', 'start']);

    expect(signOut).toHaveBeenCalledWith({ scope: 'local' });
    expect(service.session()).toBeNull();
    expect((service as any).cache.clearAll).toHaveBeenCalled();
    expect(router.navigate).toHaveBeenCalledWith(['/m', 'start']);
  });

  it('revokes this phone\'s push token while still signed in, then clears the session', async () => {
    spyOn(window, 'fetch').and.resolveTo(new Response(JSON.stringify(config), { status: 200 }));
    getSession.and.resolveTo({ data: { session: storedSession }, error: null });
    const order: string[] = [];
    const signOut = jasmine.createSpy('signOut').and.callFake(async () => {
      order.push('signOut');
      return { error: null };
    });
    (service as any).buildClient.and.returnValue({
      auth: { getSession, signOut, onAuthStateChange: jasmine.createSpy('onAuthStateChange') },
    });
    await service.init();
    spyOn(Capacitor, 'isNativePlatform').and.returnValue(true);
    const push = { revoke: jasmine.createSpy('revoke').and.callFake(async () => {
      // The revoke call needs the bearer token: the session must still be there.
      order.push(service.session() ? 'revoke-signed-in' : 'revoke-signed-out');
    }) };
    (service as any).injector = { get: (token: { prototype?: { revoke?: unknown } }) => (token?.prototype?.revoke ? push : null) };

    await service.signOut(['/m', 'start']);

    expect(order).toEqual(['revoke-signed-in', 'signOut']);
    expect(service.session()).toBeNull();
  });
});
