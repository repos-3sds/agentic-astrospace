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
 * the reader says yes, with the email switch at the end of setup (applySignupDefaults) or a switch.
 *
 * What the screen shows is the server's last answer with every switch still
 * on its way overlaid on top. Each PUT answers with the whole state, so
 * letting an answer replace the screen outright made switches the reader had
 * just tapped flip back, then on again as their own answers landed (Deepak,
 * 2026-10-28, on a slow connection). Calls go one at a time, so each answer
 * is newer than the last; a tap superseded by a later tap on the same switch
 * is never sent.
 */
@Injectable({ providedIn: 'root' })
export class EmailSettingsService {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);

  readonly state = signal<EmailState | null>(null);
  readonly error = signal<string | null>(null);

  /** The server's last answer, before pending taps are laid over it. */
  private confirmed: EmailState | null = null;
  /** Taps not yet answered, by switch; `seq` tells the latest tap apart. */
  private readonly pending = new Map<EmailCategory, { enabled: boolean; seq: number }>();
  private seq = 0;
  private queue: Promise<unknown> = Promise.resolve();

  load(): Promise<void> {
    if (!this.auth.isAuthenticated()) return Promise.resolve();
    return this.enqueue(async () => {
      try {
        this.confirm(await this.api.get<EmailState>('/me/email'));
        this.error.set(null);
      } catch {
        this.error.set('Email settings could not be loaded. Check your connection and try again.');
      }
    });
  }

  /**
   * The reader left the sign-up box ticked: turn every email on. The server
   * does nothing if they have already made any email choice. Never throws;
   * onboarding must not wait on or fail because of email.
   */
  applySignupDefaults(): Promise<void> {
    if (!this.auth.isAuthenticated()) return Promise.resolve();
    return this.enqueue(async () => {
      try {
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        this.confirm(await this.api.post<EmailState>('/me/email/defaults', { timezone, source: 'signup' }));
      } catch {
        // Left off; the reader can still turn emails on in Settings.
      }
    });
  }

  /** Flips one switch at once; the server catches up behind it. */
  set(category: EmailCategory, enabled: boolean): Promise<void> {
    const seq = ++this.seq;
    this.pending.set(category, { enabled, seq });
    this.show();
    return this.enqueue(async () => {
      // A later tap on the same switch carries the value to send.
      if (this.pending.get(category)?.seq !== seq) return;
      try {
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        const fresh = await this.api.put<EmailState>(`/me/email/${category}`, { enabled, timezone });
        this.settle(category, seq);
        this.confirm(fresh);
        this.error.set(null);
      } catch {
        // Only this switch goes back; any other tap still in flight stays.
        this.settle(category, seq);
        this.show();
        this.error.set('That change was not saved. Try again.');
      }
    });
  }

  private enqueue(job: () => Promise<void>): Promise<void> {
    const run = this.queue.then(job);
    this.queue = run.catch(() => undefined);
    return run;
  }

  private settle(category: EmailCategory, seq: number): void {
    if (this.pending.get(category)?.seq === seq) this.pending.delete(category);
  }

  private confirm(fresh: EmailState): void {
    this.confirmed = fresh;
    this.show();
  }

  private show(): void {
    const base = this.confirmed ?? this.state();
    if (!base) return;
    const categories = { ...base.categories };
    for (const [category, { enabled }] of this.pending) categories[category] = enabled;
    this.state.set({ ...base, categories });
  }
}
