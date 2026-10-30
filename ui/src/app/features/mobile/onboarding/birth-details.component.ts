import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { AnalyticsService } from '../../../core/analytics.service';
import { AuthService } from '../../../core/auth.service';
import { KundliStore } from '../../../core/kundli.store';
import { KundliPayload } from '../../../core/models';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { BirthDetailsFormComponent } from '../shared/birth-details-form.component';

/**
 * The name typed at Register, carried into the first profile. Stored by the
 * auth screen in localStorage; Supabase also keeps it in user metadata
 * (`name` for email sign-up, `full_name` for Google), which is what survives
 * a reinstall. "My chart" only when nothing is known.
 */
export function registeredName(metadata: Record<string, unknown> | undefined | null): string {
  const stored = (() => { try { return localStorage.getItem('astrospace.onboardingName'); } catch { return null; } })();
  const fromMeta = [metadata?.['name'], metadata?.['full_name']].find((v) => typeof v === 'string' && v.trim());
  return (stored?.trim() || (fromMeta as string | undefined)?.trim() || 'My chart');
}

/**
 * Birth Details (Figma node 11:2) — the last step of onboarding.
 *
 * The fields, the place search and the validation are the shared
 * `as-birth-details-form`; this screen adds the headline, fixes the
 * relationship to "self" and decides where the new profile leads.
 */
@Component({
  selector: 'as-birth-details',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackLinkDirective, BirthDetailsFormComponent],
  template: `
    <header class="topbar">
      <a class="back" [asBack]="['/m', 'customize']" aria-label="Back">
        <img src="mobile/back.svg" alt="" aria-hidden="true" />
      </a>
      <p class="step">SETUP 5 OF 5</p>
    </header>

    <h1 class="headline">Begin with your birth rhythm</h1>
    <p class="lede">These details anchor your life map. Daily timings follow your phone’s timezone, or a city you choose in Settings.</p>
    <as-birth-details-form
      class="form"
      nameLabel="WHO IS THIS FOR?"
      lockRelation="self"
      [initial]="initial"
      submitLabel="Begin my guide"
      busyLabel="Preparing your guide…"
      submitIcon="mobile/cast.svg"
      [saving]="saving()"
      [error]="error()"
      (submitted)="castChart($event)"
    />

  `,
  styleUrl: './birth-details.component.scss',
  // Outside the shell, so the token host class must be applied here or every
  // var() silently falls back — see the build plan's first convention.
  host: { class: 'as-mobile' },
})
export class BirthDetailsComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly analytics = inject(AnalyticsService);


  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  protected readonly initial: Partial<KundliPayload> = {
    name: registeredName(this.auth.user()?.user_metadata),
    relation: 'self',
  };

  protected async castChart(payload: KundliPayload): Promise<void> {
    this.saving.set(true);
    this.error.set(null);
    try {
      // Re-entering onboarding (system back from Insight, a typed URL) must
      // not mint a second "self" profile; the route guard redirects before
      // this screen renders, and this is the belt to its braces.
      await this.kundlis.load().catch(() => undefined);
      const existingSelf = this.kundlis.kundlis().find((k) => (k.relation ?? '').toLowerCase() === 'self');
      if (existingSelf) {
        this.kundlis.setActive(existingSelf.id);
        localStorage.removeItem('astrospace.onboardingName');
        await this.router.navigate(['/m', 'today']);
        return;
      }
      const created = await this.kundlis.create({ ...payload, relation: 'self' });
      this.kundlis.setActive(created.id);
      localStorage.removeItem('astrospace.onboardingName');
      this.analytics.track('onboarding_completed', { birth_time: payload.birth_time_accuracy ?? null });
      await this.router.navigate(['/m', 'insight']);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.saving.set(false);
    }
  }
}
