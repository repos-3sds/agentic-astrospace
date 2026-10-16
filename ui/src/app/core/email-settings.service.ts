import { Injectable, inject, signal } from '@angular/core';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';

/** Backend email categories (astrospace/db/crud_mobile.py EMAIL_CATEGORIES). */
export type EmailCategory =
  | 'daily_email'
  | 'festival_email'
  | 'weekly_email'
  | 'monthly_email'
  | 'lessons_email'
  | 'tips_email';

/**
 * The sign-up email box, carried from Register to the end of onboarding in
 * localStorage (the account may not exist yet, and email confirmation or
 * Google sign-in leaves the app and comes back).
 */
const OPT_IN_KEY = 'astrospace.emailOptIn';

export function rememberEmailOptIn(on: boolean): void {
  try { localStorage.setItem(OPT_IN_KEY, on ? 'yes' : 'no'); } catch { /* private mode */ }
}

/** 'yes', 'no', or null when the reader never saw the box. */
export function storedEmailOptIn(): 'yes' | 'no' | null {
  try {
    const value = localStorage.getItem(OPT_IN_KEY);
    return value === 'yes' || value === 'no' ? value : null;
  } catch {
    return null;
  }
}

export function clearEmailOptIn(): void {
  try { localStorage.removeItem(OPT_IN_KEY); } catch { /* private mode */ }
}

export interface EmailState {
  address: string | null;
  deliverable: boolean;
  suppressed_reason: string | null;
  categories: Record<EmailCategory, boolean>;
}

/**
 * The reader's email choices, held on the server only: unlike push, an
 * email can be turned off from a link in the email itself, so a copy on the
 * device would go stale. Every category starts off; nothing is emailed until
 * the reader says yes, with the sign-up box (applySignupDefaults) or a switch.
 */
@Injectable({ providedIn: 'root' })
export class EmailSettingsService {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);

  readonly state = signal<EmailState | null>(null);
  readonly error = signal<string | null>(null);

  async load(): Promise<void> {
    if (!this.auth.isAuthenticated()) return;
    try {
      this.state.set(await this.api.get<EmailState>('/me/email'));
      this.error.set(null);
    } catch {
      this.error.set('Email settings could not be loaded. Check your connection and try again.');
    }
  }

  /**
   * The reader left the sign-up box ticked: turn every email on. The server
   * does nothing if they have already made any email choice. Never throws;
   * onboarding must not wait on or fail because of email.
   */
  async applySignupDefaults(): Promise<void> {
    if (!this.auth.isAuthenticated()) return;
    try {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      this.state.set(await this.api.post<EmailState>('/me/email/defaults', { timezone, source: 'signup' }));
    } catch {
      // Left off; the reader can still turn emails on in Settings.
    }
  }

  async set(category: EmailCategory, enabled: boolean): Promise<void> {
    const before = this.state();
    if (before) this.state.set({ ...before, categories: { ...before.categories, [category]: enabled } });
    try {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      this.state.set(await this.api.put<EmailState>(`/me/email/${category}`, { enabled, timezone }));
      this.error.set(null);
    } catch {
      this.state.set(before);
      this.error.set('That change was not saved. Try again.');
    }
  }
}
