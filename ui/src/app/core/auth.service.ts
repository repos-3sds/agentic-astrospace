import { Injectable, computed, signal } from '@angular/core';
import { Router } from '@angular/router';
import { App as CapacitorApp, URLOpenListenerEvent } from '@capacitor/app';
import { Browser } from '@capacitor/browser';
import { Capacitor } from '@capacitor/core';
import { createClient, Session, SupabaseClient, User } from '@supabase/supabase-js';
import { apiUrl } from './api-origin';

const NATIVE_AUTH_CALLBACK = 'app.astrospace.mobile://auth/callback';
const NATIVE_AUTH_DESTINATION_KEY = 'astrospace.nativeAuthDestination';

interface AuthConfig {
  enabled: boolean;
  supabase_url?: string;
  supabase_anon_key?: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  readonly ready = signal(false);
  readonly enabled = signal(false);
  readonly session = signal<Session | null>(null);
  readonly user = signal<User | null>(null);
  readonly email = computed(() => this.user()?.email ?? 'Local workspace');

  private client: SupabaseClient | null = null;
  private initPromise: Promise<void> | null = null;
  private nativeCallbackInstalled = false;

  constructor(private router: Router) {}

  init(): Promise<void> {
    if (this.initPromise) return this.initPromise;
    this.initPromise = this.load();
    return this.initPromise;
  }

  private async load(): Promise<void> {
    const res = await fetch(apiUrl('/api/v1/auth/config'));
    if (!res.ok) throw new Error('Could not load auth configuration');
    const config = (await res.json()) as AuthConfig;
    this.enabled.set(!!config.enabled);

    if (!config.enabled) {
      this.ready.set(true);
      return;
    }
    if (!config.supabase_url || !config.supabase_anon_key) {
      throw new Error('Supabase auth is enabled but URL/anon key are missing');
    }

    this.client = createClient(config.supabase_url, config.supabase_anon_key, {
      auth: {
        flowType: 'pkce',
        detectSessionInUrl: !Capacitor.isNativePlatform(),
      },
    });
    await this.installNativeAuthCallback();
    const { data, error } = await this.client.auth.getSession();
    if (error) throw error;
    this.setSession(data.session);
    this.client.auth.onAuthStateChange((_event, session) => this.setSession(session));
    this.ready.set(true);
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
      options: { data: { name } },
    });
    if (error) throw error;
    this.setSession(data.session);
    if (data.session) await this.router.navigate(destination);
  }

  async signInWithMagicLink(email: string, destination = '/'): Promise<void> {
    await this.init();
    if (!this.client) return;
    const { error } = await this.client.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: this.authRedirect(destination),
      },
    });
    if (error) throw error;
  }

  async signInWithGoogle(destination = '/'): Promise<void> {
    await this.init();
    if (!this.client) return;
    const { data, error } = await this.client.auth.signInWithOAuth({
      provider: 'google',
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
      redirectTo: this.authRedirect(destination),
    });
    if (error) throw error;
  }

  async updatePassword(password: string): Promise<void> {
    await this.init();
    if (!this.client) return;
    const { error } = await this.client.auth.updateUser({ password });
    if (error) throw error;
  }

  async signOut(destination?: string[]): Promise<void> {
    await this.init();
    if (this.client) {
      const { error } = await this.client.auth.signOut({ scope: 'local' });
      if (error) throw error;
    }
    this.setSession(null);
    await this.router.navigate(destination ?? (this.enabled() ? ['/auth'] : ['/']));
  }

  async getAccessToken(): Promise<string | null> {
    await this.init();
    if (!this.enabled()) return null;
    const current = this.session();
    if (current?.access_token) return current.access_token;
    const { data } = await this.client!.auth.getSession();
    this.setSession(data.session);
    return data.session?.access_token ?? null;
  }

  isAuthenticated(): boolean {
    return !this.enabled() || !!this.session();
  }

  private setSession(session: Session | null): void {
    this.session.set(session);
    this.user.set(session?.user ?? null);
  }

  private authRedirect(destination: string): string {
    if (!Capacitor.isNativePlatform()) {
      return new URL(destination, window.location.origin).toString();
    }
    localStorage.setItem(NATIVE_AUTH_DESTINATION_KEY, destination);
    return NATIVE_AUTH_CALLBACK;
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
    if (!this.client || !url.startsWith(NATIVE_AUTH_CALLBACK)) return;
    const parsed = new URL(url);
    const fragment = new URLSearchParams(parsed.hash.replace(/^#/, ''));
    const errorDescription =
      parsed.searchParams.get('error_description') ?? fragment.get('error_description');
    if (errorDescription) throw new Error(errorDescription);

    let sessionEstablished = false;
    const code = parsed.searchParams.get('code');
    if (code) {
      const { data, error } = await this.client.auth.exchangeCodeForSession(code);
      if (error) throw error;
      this.setSession(data.session);
      sessionEstablished = !!data.session;
    } else {
      const accessToken = fragment.get('access_token');
      const refreshToken = fragment.get('refresh_token');
      if (accessToken && refreshToken) {
        const { data, error } = await this.client.auth.setSession({
          access_token: accessToken,
          refresh_token: refreshToken,
        });
        if (error) throw error;
        this.setSession(data.session);
        sessionEstablished = !!data.session;
      }
    }
    if (!sessionEstablished) return;

    await Browser.close().catch(() => undefined);
    const destination = localStorage.getItem(NATIVE_AUTH_DESTINATION_KEY) || '/m/today';
    localStorage.removeItem(NATIVE_AUTH_DESTINATION_KEY);
    await this.router.navigateByUrl(destination);
  }
}
