import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/auth.service';
import { KundliStore } from '../../../core/kundli.store';

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
  imports: [RouterLink],
  templateUrl: './account-privacy.component.html',
  styleUrl: './account-privacy.component.scss',
})
export class AccountPrivacyComponent {
  private readonly auth = inject(AuthService);
  private readonly kundlis = inject(KundliStore);
  private readonly router = inject(Router);

  protected readonly busy = signal<string | null>(null);
  protected readonly message = signal<string | null>(null);
  protected readonly error = signal<string | null>(null);
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
      await this.router.navigate(['/m', 'auth'], { queryParams: { email: this.auth.email() } });
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.busy.set(null);
    }
  }
}
