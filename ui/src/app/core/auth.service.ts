import { Injectable, Injector, computed, signal } from '@angular/core';
import { Router } from '@angular/router';
import { App as CapacitorApp, URLOpenListenerEvent } from '@capacitor/app';
import { Browser } from '@capacitor/browser';
import { Capacitor } from '@capacitor/core';
import { SocialLogin } from '@capgo/capacitor-social-login';
import { createClient, Session, SupabaseClient, User } from '@supabase/supabase-js';
import { apiUrl } from './api-origin';
import { Preferences } from '@capacitor/preferences';
import { ConnectivityService } from './connectivity.service';
import { ResourceCacheService } from './resource-cache.service';
import { SessionStorageAdapter, sessionStorageAdapter } from './session-storage';
import { SessionTeardown } from './session-teardown';

const NATIVE_AUTH_CALLBACK = 'app.asksiddha.mobile://auth/callback';
const NATIVE_AUTH_BRIDGE_PATH = '/api/v1/auth/native-callback';
/**
 * Where links in sign-in emails land: a small page on the public site that
 * says what happened and has one "Open Siddha" button (firebase-public/open.html).
 * Email links are tapped in a mail app, so they open in the phone's browser,
 * not in the in-app sheet an OAuth sign-in uses; sending them straight to the
 * custom scheme failed silently in Gmail's browser and left no way back when
 * the link had expired. Without a redirect at all, Supabase fell back to its
 * Site URL, the Cloud Run web app, which is the owner's tool, not the reader's.
 */
export const EMAIL_LINK_PAGE = 'https://asksiddha.app/open';
/** Which email a link came from, so the open page and the app can word what happened. */
export type EmailLinkKind = 'confirm' | 'signin' | 'reset' | 'email';
const NATIVE_AUTH_DESTINATION_KEY = 'astrospace.nativeAuthDestination';
const NATIVE_AUTH_STATE_KEY = 'astrospace.nativeAuthState';
// Long enough to survive a slow inbox check, short enough to bound how long a
// captured callback URL stays redeemable.
const NATIVE_AUTH_STATE_TTL_MS = 10 * 60 * 1000;
/**
 * The last /auth/config the app fetched, kept so a relaunch with no network
 * can still build the Supabase client and read the stored session. The
 * values are the project URL and the anon key, both public by design.
 */
const AUTH_CONFIG_CACHE_KEY = 'astrospace.authConfig';
/** The most any single boot-time network step may hold the splash. */
const BOOT_NETWORK_TIMEOUT_MS = 8_000;

function withTimeout<T>(work: Promise<T>, ms: number, fallback: () => T): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<T>((resolve) => {
    timer = setTimeout(() => resolve(fallback()), ms);
  });
  return Promise.race([work, timeout]).finally(() => clearTimeout(timer));
}

/** The key supabase-js persists its session under when no storageKey is configured. */
export function supabaseStorageKey(supabaseUrl: string): string {
  const ref = new URL(supabaseUrl).hostname.split('.')[0];
  return `sb-${ref}-auth-token`;
}

/** crypto.randomUUID() is unavailable on some older WKWebView builds. */
function randomNonce(): string {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}

/** SHA-256 of a string as lowercase hex, the form Google puts in an ID token's nonce. */
export async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Android reports USER_CANCELLED; iOS's GIDSignIn says "The user canceled the
 * sign-in flow."; Apple's sheet reports AuthorizationError 1001.
 */
function isSignInCancel(error: unknown): boolean {
  const { code, message } = (error ?? {}) as { code?: unknown; message?: unknown };
  return code === 'USER_CANCELLED' || /cancel|AuthorizationError error 1001/i.test(String(message ?? ''));
}

interface AuthConfig {
  enabled: boolean;
  supabase_url?: string;
  supabase_anon_key?: string;
  /** Public OAuth client IDs; with them the phone apps use Google's own sign-in sheet. */
  google_web_client_id?: string | null;
  google_ios_client_id?: string | null;
}

/** How long sign-out waits for the push-token revoke before going ahead. */
const PUSH_REVOKE_MAX_WAIT_MS = 4_000;

@Injectable({ providedIn: 'root' })
export class AuthService {
  readonly ready = signal(false);
  readonly enabled = signal(false);
  /**
   * True from a sign-out until the next sign-in. With auth disabled (dev,
   * e2e) `isAuthenticated()` is always true, so this is the only way the
   * onboarding guard can tell a signed-out person from an onboarded one.
   */
  readonly signedOut = signal(false);
  readonly session = signal<Session | null>(null);
  readonly user = signal<User | null>(null);
  readonly email = computed(() => this.user()?.email ?? 'Local workspace');

  private client: SupabaseClient | null = null;
  private initPromise: Promise<void> | null = null;
  private nativeCallbackInstalled = false;
  private readonly connectivity: ConnectivityService;
  /**
   * Keychain / Keystore on a device, Preferences in a browser — see
   * session-storage.ts. One adapter instance serves both supabase-js and the
   * offline fallback read in load(), so they can never disagree about where
   * the session is.
   */
  private readonly sessionStorage: SessionStorageAdapter = sessionStorageAdapter();
  /** The project the client was built for; public values, used for its settings endpoint. */
  private supabaseProject: { url: string; anonKey: string } | null = null;
  private googleClientIds: { web: string; ios: string | null } | null = null;
  private socialLoginReady: Promise<void> | null = null;
  private appleLoginReady: Promise<void> | null = null;
  /** The native Google plugin; a field so specs can hand in a fake. */
  protected socialLogin: Pick<typeof SocialLogin, 'initialize' | 'login' | 'logout'> = SocialLogin;

  constructor(
    private router: Router,
    connectivity: ConnectivityService,
    private readonly cache: ResourceCacheService,
    // Optional so specs can `new AuthService(...)` without an injector.
    private readonly injector?: Injector,
  ) {
    this.connectivity = connectivity;
  }

  init(): Promise<void> {
    if (this.initPromise) return this.initPromise;
    this.initPromise = this.load().catch((error) => {
      this.initPromise = null;
      throw error;
    });
    return this.initPromise;
  }

  private async load(): Promise<void> {
    const config = await this.loadConfig();
    this.enabled.set(!!config.enabled);

    if (!config.enabled) {
      this.ready.set(true);
      return;
    }
    if (!config.supabase_url || !config.supabase_anon_key) {
      throw new Error('Supabase auth is enabled but URL/anon key are missing');
    }

    this.client = this.buildClient(config.supabase_url, config.supabase_anon_key);
    this.supabaseProject = { url: config.supabase_url, anonKey: config.supabase_anon_key };
    this.googleClientIds = config.google_web_client_id
      ? { web: config.google_web_client_id, ios: config.google_ios_client_id ?? null }
      : null;
    await this.installNativeAuthCallback();
    this.installAutoRefreshLifecycle();
    // Bounded: with an expired access token getSession() refreshes over the
    // network, and supabase-js retries a failing refresh with backoff for up
    // to ~30 s. Past the bound the stored session stands in (same rule as the
    // offline branch below) and onAuthStateChange applies the refreshed one
    // whenever it lands.
    const { data, error } = await withTimeout<{ data: { session: Session | null }; error: Error | null }>(
      this.client.auth.getSession(),
      BOOT_NETWORK_TIMEOUT_MS,
      // Only a refresh can take this long, and a refresh means a stored
      // session exists; so no error here, the stored session is used below.
      () => ({ data: { session: null }, error: null }),
    );
    if (error || !data.session) {
      // Offline, supabase-js cannot refresh an expired session and reports
      // that as an error (or no session). The stored session is still the
      // person's, and the encrypted cache behind the shell is keyed to it,
      // so a relaunch with no network keeps them signed in on what is
      // saved rather than bouncing them to the sign-in screen. API calls
      // fail honestly until the connection returns; the shell banner says
      // so. A real sign-out clears this storage, so it is never resurrected.
      const stored = await this.storedSession(config.supabase_url);
      if (error && !stored) throw error;
      this.setSession(stored ?? data.session);
    } else {
      this.setSession(data.session);
    }
    this.client.auth.onAuthStateChange((event, session) => {
      // Only SIGNED_OUT ends a session. supabase-js reports INITIAL_SESSION
      // with null whenever its own getSession() fails, which is every offline
      // launch with an expired access token; until 2026-10-17 that null
      // signed the reader out moments after the stored session above had
      // kept them in, and an offline launch landed on the welcome screen.
      if (!session && event !== 'SIGNED_OUT') return;
      this.setSession(session);
    });
    this.ready.set(true);
  }

  /**
   * Cache first, revalidated in the background. The config is the Supabase
   * project URL and anon key, which change on a key rotation and essentially
   * never otherwise, so a cold start must not wait on the network for them:
   * until 2026-10-15 every launch fetched first, with no timeout, and a slow
   * network held the splash. A first launch (nothing cached) still fetches,
   * bounded by BOOT_NETWORK_TIMEOUT_MS. A revalidated config that differs is
   * stored and takes effect on the next launch — rebuilding the Supabase
   * client under a live session is riskier than one stale launch.
   */
  private async loadConfig(): Promise<AuthConfig> {
    const cached = await this.cachedConfig();
    if (cached) {
      void this.fetchConfig().catch(() => undefined);
      return cached;
    }
    return this.fetchConfig();
  }

  private async fetchConfig(): Promise<AuthConfig> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), BOOT_NETWORK_TIMEOUT_MS);
    try {
      const res = await fetch(apiUrl('/api/v1/auth/config'), { signal: controller.signal });
      this.connectivity.noteRequestSuccess();
      if (!res.ok) throw new Error('Could not load auth configuration');
      const config = (await res.json()) as AuthConfig;
      await Preferences.set({ key: AUTH_CONFIG_CACHE_KEY, value: JSON.stringify(config) }).catch(() => undefined);
      return config;
    } catch (error) {
      // An abort is a timeout, which for boot purposes is unreachable.
      this.connectivity.noteRequestFailure(
        controller.signal.aborted ? new TypeError('Failed to fetch (timed out)') : error,
      );
      throw error;
    } finally {
      clearTimeout(timer);
    }
  }

  private async cachedConfig(): Promise<AuthConfig | null> {
    try {
      const { value } = await Preferences.get({ key: AUTH_CONFIG_CACHE_KEY });
      if (!value) return null;
      const parsed = JSON.parse(value) as Partial<AuthConfig>;
      return typeof parsed.enabled === 'boolean' ? (parsed as AuthConfig) : null;
    } catch {
      return null;
    }
  }

  /** supabase-js's persisted session, read directly from the same storage it writes. */
  private async storedSession(supabaseUrl: string): Promise<Session | null> {
    try {
      const value = await this.sessionStorage.getItem(supabaseStorageKey(supabaseUrl));
      if (!value) return null;
      const parsed = JSON.parse(value) as Partial<Session>;
      return parsed?.access_token && parsed.user ? (parsed as Session) : null;
    } catch {
      return null;
    }
  }

  /** Separate so tests can hand the service a fake client without touching the network. */
  protected buildClient(url: string, anonKey: string): SupabaseClient {
    return createClient(url, anonKey, {
      auth: {
        flowType: 'pkce',
        detectSessionInUrl: !Capacitor.isNativePlatform(),
        storage: this.sessionStorage,
      },
    });
  }

  /**
   * supabase-js's autoRefreshToken runs on a JS timer, and iOS/Android freeze
   * JS timers while the app is backgrounded. A user who leaves the app open
   * in the background for longer than the access token's lifetime (1h by
   * default) comes back to a client that never noticed the token expired —
   * this is Supabase's own documented gotcha for Capacitor/React Native, not
   * something autoRefreshToken:true (the default) covers by itself. The fix
   * they document: drive start/stop off the app's own foreground lifecycle
   * instead of trusting the timer to survive suspension.
   */
  private installAutoRefreshLifecycle(): void {
    if (!Capacitor.isNativePlatform()) return;
    void CapacitorApp.addListener('appStateChange', ({ isActive }) => {
      if (isActive) {
        void this.client?.auth.startAutoRefresh();
        void this.refreshForegroundSession();
      } else {
        void this.client?.auth.stopAutoRefresh();
      }
    });
  }

  private async refreshForegroundSession(): Promise<void> {
    if (!this.client || !this.session()) return;
    const { data, error } = await this.client.auth.getSession();
    // A foreground network transition is not a sign-out. Supabase's auth-state
    // callback remains the authority for a real SIGNED_OUT event; keeping the
    // last session here prevents a brief offline/online handoff from ejecting
    // the reader from every guarded mobile route.
    if (!error && data.session) this.setSession(data.session);
  }

  async signIn(email: string, password: string, destination: string[] = ['/app']): Promise<void> {
    await this.init();
    if (!this.client) return;
    const { data, error } = await this.client.auth.signInWithPassword({ email, password });
    if (error) throw error;
    this.setSession(data.session);
    if (destination.length) await this.router.navigate(destination);
  }

  async signUp(
    email: string,
    password: string,
    name: string,
    destination: string[] = ['/app'],
  ): Promise<void> {
    await this.init();
    if (!this.client) return;
    const { data, error } = await this.client.auth.signUp({
      email,
      password,
      options: {
        data: { name },
        emailRedirectTo: this.emailLinkRedirect('/' + destination.join('/').replace(/^\/+/, ''), 'confirm'),
      },
    });
    if (error) throw error;
    this.setSession(data.session);
    if (data.session) await this.router.navigate(destination);
  }

  /** Sends the sign-up confirmation email again, for an account not yet confirmed. */
  async resendConfirmation(email: string, destination = '/m/birth-details'): Promise<void> {
    await this.init();
    if (!this.client) return;
    const { error } = await this.client.auth.resend({
      type: 'signup',
      email,
      options: { emailRedirectTo: this.emailLinkRedirect(destination, 'confirm') },
    });
    if (error) throw error;
  }

  async signInWithMagicLink(email: string, destination = '/'): Promise<void> {
    await this.init();
    if (!this.client) return;
    const { error } = await this.client.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: this.emailLinkRedirect(destination, 'signin'),
      },
    });
    if (error) throw error;
  }

  /**
   * On a phone, Google's own sign-in sheet (Credential Manager on Android,
   * the Google Sign-In SDK on iOS), whose ID token goes straight to Supabase.
   * No browser page opens, so the reader never sees the Supabase project
   * address that Google shows for the hosted flow. Anything short of a
   * cancel falls back to the hosted flow, so a Cloud Console setup that is
   * not finished yet costs nothing worse than the old behaviour.
   */
  async signInWithGoogle(destination = '/'): Promise<void> {
    await this.init();
    if (!this.client) return;
    if (await this.signInWithNativeGoogle(destination)) return;
    await this.signInWithProvider('google', destination);
  }

  /** True when the native sheet finished (signed in or cancelled); false means use the browser. */
  private async signInWithNativeGoogle(destination: string): Promise<boolean> {
    const ids = this.googleClientIds;
    const platform = Capacitor.getPlatform();
    if (!this.client || !ids || !Capacitor.isNativePlatform()) return false;
    // iOS needs its own client, plus that client's reversed ID as a URL
    // scheme in Info.plist; until both exist the server leaves it unset.
    if (platform === 'ios' && !ids.ios) return false;
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      throw new Error('No connection. Check your internet and try again.');
    }
    // Google signs the hash into the token; Supabase is given the raw value
    // and checks one against the other, so a captured token can't be replayed.
    const rawNonce = randomNonce();
    let idToken: string | null = null;
    try {
      await this.initSocialLogin(ids);
      const login = await this.socialLogin.login({
        provider: 'google',
        options: { nonce: await sha256Hex(rawNonce) },
      });
      idToken = 'idToken' in login.result ? login.result.idToken : null;
    } catch (error) {
      if (isSignInCancel(error)) return true;
      console.warn('Native Google sign-in unavailable; using the browser', error);
      return false;
    }
    if (!idToken) return false;
    const { data, error } = await this.client.auth.signInWithIdToken({
      provider: 'google',
      token: idToken,
      nonce: rawNonce,
    });
    if (error) {
      // Typically the iOS client ID missing from Supabase's authorised list.
      console.warn('Supabase refused the native Google token; using the browser', error);
      return false;
    }
    this.setSession(data.session);
    await this.router.navigateByUrl(destination);
    return true;
  }

  private initSocialLogin(ids: { web: string; ios: string | null }): Promise<void> {
    this.socialLoginReady ??= this.socialLogin.initialize({
      google: {
        webClientId: ids.web,
        iOSClientId: ids.ios ?? undefined,
        iOSServerClientId: ids.web,
        mode: 'online',
      },
    }).catch((error) => {
      this.socialLoginReady = null;
      throw error;
    });
    return this.socialLoginReady;
  }

  /**
   * Sign in with Apple. App Review (guideline 4.8) requires it on iOS because
   * Google sign-in is offered; the screen shows it only on iOS and only once
   * `appleSignInEnabled()` says the project has it switched on.
   *
   * On the iPhone this is Apple's own sheet, which names Siddha and shows its
   * icon; its identity token goes straight to Supabase. The hosted flow
   * opened a browser page that named the Supabase project address instead
   * (Hawk, 2026-10-26). Anything short of a cancel falls back to that flow.
   */
  async signInWithApple(destination = '/'): Promise<void> {
    await this.init();
    if (!this.client) return;
    if (await this.signInWithNativeApple(destination)) return;
    await this.signInWithProvider('apple', destination);
  }

  /** True when Apple's sheet finished (signed in or cancelled); false means use the browser. */
  private async signInWithNativeApple(destination: string): Promise<boolean> {
    if (!this.client || Capacitor.getPlatform() !== 'ios') return false;
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      throw new Error('No connection. Check your internet and try again.');
    }
    // As with Google: Apple puts the hash in the token, Supabase gets the raw value.
    const rawNonce = randomNonce();
    let idToken: string | null = null;
    let fullName: string | null = null;
    try {
      this.appleLoginReady ??= this.socialLogin.initialize({ apple: { redirectUrl: '' } }).catch((error) => {
        this.appleLoginReady = null;
        throw error;
      });
      await this.appleLoginReady;
      const login = await this.socialLogin.login({
        provider: 'apple',
        options: { scopes: ['name', 'email'], nonce: await sha256Hex(rawNonce) },
      });
      const result = login.result as { idToken?: string | null; profile?: { givenName?: string | null; familyName?: string | null } };
      idToken = result.idToken ?? null;
      // Apple sends the name on the first sign-in only, and never in the token.
      fullName = [result.profile?.givenName, result.profile?.familyName].filter(Boolean).join(' ') || null;
    } catch (error) {
      if (isSignInCancel(error)) return true;
      console.warn('Native Apple sign-in unavailable; using the browser', error);
      return false;
    }
    if (!idToken) return false;
    const { data, error } = await this.client.auth.signInWithIdToken({
      provider: 'apple',
      token: idToken,
      nonce: rawNonce,
    });
    if (error) {
      // Typically the bundle ID missing from Supabase's Apple "Client IDs".
      console.warn('Supabase refused the native Apple token; using the browser', error);
      return false;
    }
    this.setSession(data.session);
    if (fullName) void this.client.auth.updateUser({ data: { full_name: fullName } }).catch(() => undefined);
    await this.router.navigateByUrl(destination);
    return true;
  }

  /**
   * Whether the Supabase project has the Apple provider switched on, read from
   * its public settings endpoint. False on any failure, so a button that
   * would open Supabase's "provider is not enabled" page is never shown.
   */
  async appleSignInEnabled(): Promise<boolean> {
    try {
      await this.init();
    } catch {
      return false;
    }
    const project = this.supabaseProject;
    if (!project) return false;
    try {
      const res = await fetch(`${project.url}/auth/v1/settings`, { headers: { apikey: project.anonKey } });
      if (!res.ok) return false;
      const settings = (await res.json()) as { external?: Record<string, boolean> };
      return settings.external?.['apple'] === true;
    } catch {
      return false;
    }
  }

  private async signInWithProvider(provider: 'google' | 'apple', destination: string): Promise<void> {
    await this.init();
    if (!this.client) return;
    // Offline, the browser would open on its own "no internet" page.
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      throw new Error('No connection. Check your internet and try again.');
    }
    const { data, error } = await this.client.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: this.authRedirect(destination),
        skipBrowserRedirect: Capacitor.isNativePlatform(),
      },
    });
    if (error) throw error;
    if (Capacitor.isNativePlatform() && data.url) await Browser.open({ url: data.url });
  }

  async resetPassword(email: string, destination = '/m/auth'): Promise<void> {
    await this.init();
    if (!this.client) return;
    const { error } = await this.client.auth.resetPasswordForEmail(email, {
      redirectTo: this.emailLinkRedirect(destination, 'reset'),
    });
    if (error) throw error;
  }

  async updatePassword(password: string): Promise<void> {
    await this.init();
    if (!this.client) return;
    const { error } = await this.client.auth.updateUser({ password });
    if (error) throw error;
  }

  /**
   * Ask Supabase to move the account to a new address. Nothing changes until
   * the link in the confirmation email is opened (with secure email change on,
   * the current address gets one too), so the caller says so rather than
   * reporting the change as done. Flow audit 2026-10-15, item 4.6: the row
   * used to open the sign-in screen instead.
   */
  async changeEmail(email: string, destination = '/m/settings/account'): Promise<void> {
    await this.init();
    if (!this.client) throw new Error('Email changes need a signed-in account.');
    const { error } = await this.client.auth.updateUser(
      { email },
      { emailRedirectTo: this.emailLinkRedirect(destination, 'email') },
    );
    if (error) throw error;
  }

  async signOut(destination?: string[]): Promise<void> {
    await this.init();
    // Revoke before the session goes: the API call needs the bearer token,
    // and a signed-out phone must not keep receiving this account's briefs.
    // Until 2026-10-16 this ran after auth.signOut() below had already
    // cleared the session, so every revoke went out unauthenticated, got a
    // 401, and the old account kept pushing to the phone. Capped, so a slow
    // network never holds sign-out up; the server also drops dead tokens.
    // Resolved lazily because PushService -> ApiService -> AuthService.
    if (Capacitor.isNativePlatform() && this.injector) {
      const { PushService } = await import('./push.service');
      await Promise.race([
        this.injector.get(PushService).revoke(),
        new Promise<void>((resolve) => setTimeout(resolve, PUSH_REVOKE_MAX_WAIT_MS)),
      ]);
    }
    if (this.client) {
      const { error } = await this.client.auth.signOut({ scope: 'local' });
      if (error) throw error;
    }
    // So the next person on this phone picks their own Google account.
    if (this.socialLoginReady) void this.socialLogin.logout({ provider: 'google' }).catch(() => undefined);
    this.setSession(null);
    this.signedOut.set(true);
    // Retained tab views, the profile list and every other per-user value
    // registered with SessionTeardown. Before this the footer tabs kept the
    // previous account's Today alive in the route-reuse store, so the next
    // account to sign in on the phone saw it until it re-rendered.
    this.injector?.get(SessionTeardown, null)?.run();
    // The encrypted cache holds the signed-out account's guidance, charts and
    // threads. Until 2026-10-15 it was left on disk until its TTL, so the next
    // person to sign in on a shared phone inherited it. The cache is keyed by
    // user, but a sign-out means "nothing of mine stays on this device".
    this.cache.clearAll();
    await this.router.navigate(destination ?? (this.enabled() ? ['/auth'] : ['/']));
  }

  async getAccessToken(): Promise<string | null> {
    await this.init();
    if (!this.enabled()) return null;
    // Was: trust the cached session's token forever once one existed. If the
    // auto-refresh timer missed its window (see installAutoRefreshLifecycle),
    // that handed out an expired token on every request until the *next*
    // auth state change, which is exactly the repeated-logout symptom this
    // fixes. client.auth.getSession() is supabase-js's own freshness check —
    // it returns the cached session with no network call when still valid,
    // and refreshes it first when it isn't. Always deferring to it here
    // means this method can't go stale independently of that logic.
    const { data, error } = await this.client!.auth.getSession();
    if (error) {
      const current = this.session();
      return this.usableAccessToken(current);
    }
    this.setSession(data.session);
    return data.session?.access_token ?? null;
  }

  isAuthenticated(): boolean {
    return !this.enabled() || !!this.session();
  }

  private setSession(session: Session | null): void {
    if (session) this.signedOut.set(false);
    this.session.set(session);
    this.user.set(session?.user ?? null);
  }

  private usableAccessToken(session: Session | null): string | null {
    if (!session?.access_token) return null;
    if (!session.expires_at) return session.access_token;
    return session.expires_at * 1000 > Date.now() + 5_000 ? session.access_token : null;
  }

  private authRedirect(destination: string): string {
    if (!Capacitor.isNativePlatform()) {
      return new URL(destination, window.location.origin).toString();
    }
    localStorage.setItem(NATIVE_AUTH_DESTINATION_KEY, destination);
    const state = this.issueNativeAuthState();
    return `${NATIVE_AUTH_CALLBACK}?state=${encodeURIComponent(state)}`;
  }

  /**
   * The redirect for a link sent by email. On the web it is the page the
   * owner asked from. In the app it is the open page on asksiddha.app, which
   * hands the link's code to the app through the custom scheme; the code is
   * only redeemable here, because the PKCE verifier never leaves this device.
   */
  private emailLinkRedirect(destination: string, kind: EmailLinkKind): string {
    if (!Capacitor.isNativePlatform()) return this.authRedirect(destination);
    localStorage.setItem(NATIVE_AUTH_DESTINATION_KEY, destination);
    return `${EMAIL_LINK_PAGE}?from=${kind}`;
  }

  /**
   * A random, one-time value bound to the auth flow this app instance just
   * started. Every legitimate callback carries it back; a URL fired by
   * another app or a tapped link has no way to know it, so anything without
   * a match is forged input, not a session — see handleNativeAuthCallback.
   */
  private issueNativeAuthState(): string {
    const nonce = randomNonce();
    localStorage.setItem(NATIVE_AUTH_STATE_KEY, JSON.stringify({ nonce, issuedAt: Date.now() }));
    return nonce;
  }

  /** One-time: consumed (and cleared) whether or not it matches. */
  private consumeNativeAuthState(received: string | null): boolean {
    const raw = localStorage.getItem(NATIVE_AUTH_STATE_KEY);
    localStorage.removeItem(NATIVE_AUTH_STATE_KEY);
    if (!raw || !received) return false;
    try {
      const { nonce, issuedAt } = JSON.parse(raw) as { nonce: string; issuedAt: number };
      if (Date.now() - issuedAt > NATIVE_AUTH_STATE_TTL_MS) return false;
      return nonce === received;
    } catch {
      return false;
    }
  }

  private async installNativeAuthCallback(): Promise<void> {
    if (!Capacitor.isNativePlatform() || this.nativeCallbackInstalled) return;
    this.nativeCallbackInstalled = true;
    await CapacitorApp.addListener('appUrlOpen', (event: URLOpenListenerEvent) => {
      void this.handleNativeAuthCallback(event.url).catch((error) => {
        console.error('Native authentication callback failed', error);
      });
    });
    const launch = await CapacitorApp.getLaunchUrl();
    if (launch?.url) await this.handleNativeAuthCallback(launch.url);
  }

  private async handleNativeAuthCallback(url: string): Promise<void> {
    if (!this.client || !this.isNativeAuthCallback(url)) return;
    await this.closeNativeAuthBrowser();
    const parsed = new URL(url);
    // Set only by the email open page (asksiddha.app/open). An email link has
    // no screen of its own to report on, so whatever happens here the reader
    // lands somewhere that says so; OAuth callbacks keep reporting through
    // the sign-in button that started them.
    const from = parsed.searchParams.get('from') as EmailLinkKind | null;
    if (!from) {
      await this.finishNativeAuthCallback(parsed);
      return;
    }
    let signedIn = false;
    try {
      signedIn = await this.finishNativeAuthCallback(parsed);
    } catch (error) {
      console.error('Email link sign-in failed', error);
    }
    if (signedIn) return;
    const fragment = new URLSearchParams(parsed.hash.replace(/^#/, ''));
    const failed = !!(parsed.searchParams.get('error') ?? fragment.get('error'));
    // A confirm link confirms the address on Supabase's side before it gets
    // here; only the sign-in that rides on it can fail (another phone, or the
    // app reinstalled since). So unless Supabase said the link itself was
    // bad, the account is confirmed and a normal sign-in finishes the job.
    let link: 'confirmed' | 'expired' | null = null;
    if (from === 'confirm' && !failed) link = 'confirmed';
    else if (failed || parsed.searchParams.has('code')) link = 'expired';
    if (link) await this.router.navigate(['/m', 'auth'], { queryParams: { link } });
  }

  /** True when the callback left a session behind. */
  private async finishNativeAuthCallback(parsed: URL): Promise<boolean> {
    if (!this.client) return false;
    const fragment = new URLSearchParams(parsed.hash.replace(/^#/, ''));
    const errorDescription =
      parsed.searchParams.get('error_description') ?? fragment.get('error_description');
    if (errorDescription) throw new Error(errorDescription);

    let sessionEstablished = false;
    const code = parsed.searchParams.get('code');
    if (code) {
      // Already safe without a state check: exchanging a code for a session
      // requires the verifier this app instance generated, so an
      // intercepted or injected code is inert on its own. Left ungated
      // deliberately — unlike the fragment branch below, there's no way to
      // confirm from here whether Supabase preserves a redirectTo query
      // string across every code-exchange path, and this branch doesn't
      // need the extra check to be safe.
      const { data, error } = await this.client.auth.exchangeCodeForSession(code);
      if (error) throw error;
      this.setSession(data.session);
      sessionEstablished = !!data.session;
    } else {
      const accessToken = fragment.get('access_token');
      const refreshToken = fragment.get('refresh_token');
      if (accessToken && refreshToken) {
        // This branch has no code-verifier equivalent, so the state check is
        // the only thing standing between it and anyone who can fire this
        // custom scheme (another installed app, a tapped web link — it's
        // registered BROWSABLE with autoVerify off) handing this app a
        // session for an account they control.
        const receivedState = parsed.searchParams.get('state') ?? fragment.get('state');
        if (!this.consumeNativeAuthState(receivedState)) {
          throw new Error('Sign-in link could not be verified. Please try again.');
        }
        const { data, error } = await this.client.auth.setSession({
          access_token: accessToken,
          refresh_token: refreshToken,
        });
        if (error) throw error;
        this.setSession(data.session);
        sessionEstablished = !!data.session;
      }
    }
    if (!sessionEstablished) return false;

    await Browser.close().catch(() => undefined);
    const destination = localStorage.getItem(NATIVE_AUTH_DESTINATION_KEY) || '/m/today';
    localStorage.removeItem(NATIVE_AUTH_DESTINATION_KEY);
    await this.router.navigateByUrl(destination);
    return true;
  }

  private isNativeAuthCallback(url: string): boolean {
    // The open page itself counts too: on Android, a verified App Link can
    // hand https://asksiddha.app/open?code=… straight to the app.
    // apiUrl() last: it throws in a build with no native API origin.
    return url.startsWith(NATIVE_AUTH_CALLBACK)
      || url.startsWith(EMAIL_LINK_PAGE)
      || url.startsWith(apiUrl(NATIVE_AUTH_BRIDGE_PATH));
  }

  private async closeNativeAuthBrowser(): Promise<void> {
    try {
      await Browser.close();
    } catch {
      // Android Custom Tabs may already be gone when the app receives the URL.
    }
  }
}
