import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/auth.service';
import { AnalyticsService } from '../../../core/analytics.service';
import { PreferencesService } from '../../../core/preferences.service';
import { KundliStore } from '../../../core/kundli.store';
import { BackLinkDirective } from '../../../core/back-link.directive';

/**
 * Settings — Account & privacy (Figma node 69:180).
 *
 * "Export my data" comes first, above sign-out and delete. Data you cannot take
 * with you is not yours, and putting export at the top is the cheapest way to
 * mean the Welcome screen's "your birth details stay yours".
 *
 * Delete is separated by a rule, outlined rather than filled, and carries its
 * consequence in text beneath it. It is deliberately **not wired**: the design
 * has no confirmation step, and an irreversible action that destroys charts,
 * notes and history should not be one tap from a settings list. Wiring it needs
 * a confirm — that is a design question, not something to invent here.
 */
@Component({
  selector: 'as-settings-account',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackLinkDirective, RouterLink],
  templateUrl: './account-privacy.component.html',
  styleUrl: './account-privacy.component.scss',
})
export class AccountPrivacyComponent {
  private readonly auth = inject(AuthService);
  private readonly kundlis = inject(KundliStore);
  private readonly router = inject(Router);
  protected readonly preferences = inject(PreferencesService);
  private readonly analytics = inject(AnalyticsService);

  protected readonly busy = signal<string | null>(null);
  protected readonly message = signal<string | null>(null);
  protected readonly error = signal<string | null>(null);
  /** The inline Change email form under its row. */
  protected readonly editingEmail = signal(false);
  protected readonly newEmail = signal('');
  /** Sign out asks once: a stray tap in Settings ended the session outright. */
  protected readonly confirmingSignOut = signal(false);
  // The real address only: `auth.email()` falls back to "Local workspace".
  protected readonly currentEmail = computed(() => this.auth.user()?.email ?? null);

  protected readonly actions = [
    { id: 'export', label: 'Export my data' },
    { id: 'email', label: 'Change email' },
    { id: 'signout', label: 'Sign out' },
  ];

  protected async run(id: string): Promise<void> {
    this.message.set(null);
    this.error.set(null);
    this.busy.set(id);
    try {
      if (id === 'signout') {
        this.confirmingSignOut.update((open) => !open);
        return;
      }
      if (id === 'signout-confirmed') {
        this.kundlis.reset();
        await this.auth.signOut(['/m', 'start']);
        return;
      }
      if (id === 'export') {
        if (!this.kundlis.loaded()) await this.kundlis.load();
        const payload = JSON.stringify({
          exportedAt: new Date().toISOString(),
          account: { email: this.auth.email() },
          profiles: this.kundlis.kundlis(),
        }, null, 2);
        const url = URL.createObjectURL(new Blob([payload], { type: 'application/json' }));
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = `siddha-export-${new Date().toISOString().slice(0, 10)}.json`;
        anchor.click();
        URL.revokeObjectURL(url);
        this.message.set('Your data export is ready.');
        return;
      }
      if (id === 'email') {
        this.editingEmail.update((open) => !open);
        this.newEmail.set('');
        return;
      }
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.busy.set(null);
    }
  }

  /**
   * Sends the confirmation link. The address only changes once that link is
   * opened, so the message says what to do next instead of "done".
   */
  protected async sendEmailChange(): Promise<void> {
    const email = this.newEmail().trim();
    this.message.set(null);
    this.error.set(null);
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      this.error.set('Enter the new email address.');
      return;
    }
    if (email.toLowerCase() === (this.currentEmail() ?? '').toLowerCase()) {
      this.error.set('That is already your email address.');
      return;
    }
    this.busy.set('email');
    try {
      await this.auth.changeEmail(email);
      this.editingEmail.set(false);
      this.message.set(
        `We sent a confirmation link to ${email}. Your email changes once you open it; if your current address gets a link too, open that one as well. Until then, keep signing in with ${this.currentEmail() ?? 'your current address'}.`,
      );
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.busy.set(null);
    }
  }

  /** Turning it off drops anything queued, so nothing more leaves the phone. */
  protected toggleShareUsage(): void {
    this.preferences.shareUsage.set(!this.preferences.shareUsage());
    // With sharing off, flush() discards the queue instead of sending it.
    this.analytics.flush();
  }
}
