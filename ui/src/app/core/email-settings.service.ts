import { Injectable, inject, signal } from '@angular/core';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';

/** Backend email categories (astrospace/db/crud_mobile.py EMAIL_CATEGORIES). */
export type EmailCategory = 'daily_email' | 'festival_email';

export interface EmailState {
  address: string | null;
  deliverable: boolean;
  suppressed_reason: string | null;
  categories: Record<EmailCategory, boolean>;
}

/**
 * The reader's email choices, held on the server only: unlike push, an
 * email can be turned off from a link in the email itself, so a copy on the
 * device would go stale. Both categories start off; nothing is emailed until
 * the reader turns one on here.
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
