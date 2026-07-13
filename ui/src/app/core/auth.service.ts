import { Injectable, computed, signal } from '@angular/core';
import { Router } from '@angular/router';
import { createClient, Session, SupabaseClient, User } from '@supabase/supabase-js';

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

  constructor(private router: Router) {}

  init(): Promise<void> {
    if (this.initPromise) return this.initPromise;
    this.initPromise = this.load();
    return this.initPromise;
  }

  private async load(): Promise<void> {
    const res = await fetch('/api/v1/auth/config');
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

    this.client = createClient(config.supabase_url, config.supabase_anon_key);
    const { data, error } = await this.client.auth.getSession();
    if (error) throw error;
    this.setSession(data.session);
    this.client.auth.onAuthStateChange((_event, session) => this.setSession(session));
    this.ready.set(true);
  }

  async signIn(email: string, password: string): Promise<void> {
    await this.init();
    if (!this.client) return;
    const { data, error } = await this.client.auth.signInWithPassword({ email, password });
    if (error) throw error;
    this.setSession(data.session);
    await this.router.navigate(['/app']);
  }

  async signUp(email: string, password: string, name: string): Promise<void> {
    await this.init();
    if (!this.client) return;
    const { data, error } = await this.client.auth.signUp({
      email,
      password,
      options: { data: { name } },
    });
    if (error) throw error;
    this.setSession(data.session);
    if (data.session) await this.router.navigate(['/app']);
  }

  async signInWithMagicLink(email: string): Promise<void> {
    await this.init();
    if (!this.client) return;
    const { error } = await this.client.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: window.location.origin,
      },
    });
    if (error) throw error;
  }

  async signInWithGoogle(): Promise<void> {
    await this.init();
    if (!this.client) return;
    const { error } = await this.client.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: window.location.origin,
      },
    });
    if (error) throw error;
  }

  async signOut(): Promise<void> {
    await this.init();
    if (this.client) {
      const { error } = await this.client.auth.signOut({ scope: 'local' });
      if (error) throw error;
    }
    this.setSession(null);
    await this.router.navigate(this.enabled() ? ['/auth'] : ['/']);
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
}
