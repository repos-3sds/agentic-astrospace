import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { KundliPayload } from '../../../core/models';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { BirthDetailsFormComponent } from '../shared/birth-details-form.component';
import { StickyBarDirective } from '../shared/sticky-bar.directive';

/**
 * Compatibility › Add a person. The same birth-details form as everywhere
 * else: a place is chosen from the search, never typed, so the saved profile
 * can always be cast (flow audit 2026-10-15, items 4.1 and 5.1).
 */
@Component({
  selector: 'as-add-prospect',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [StickyBarDirective, BackLinkDirective, BirthDetailsFormComponent],
  template: `
    <a class="mcof-back" asStickyBar [asBack]="['/m','compat']"><img src="mobile/back.svg" alt="" /><span>Compatibility</span></a>
    <section class="mcof-form">
      <header><h1>Add the person</h1><p>Create a saved profile, then compute the match from real chart data.</p></header>
      <as-birth-details-form
        [initial]="initial"
        [hideSelf]="true"
        submitLabel="Check compatibility"
        busyLabel="Saving…"
        [saving]="saving()"
        [error]="error()"
        (submitted)="submit($event)"
      />
    </section>
  `,
  styleUrl: './add-prospect.component.scss',
})
export class AddProspectComponent {
  private readonly router = inject(Router);
  private readonly kundlis = inject(KundliStore);

  protected readonly saving = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly initial: Partial<KundliPayload> = { relation: 'partner' };

  protected async submit(payload: KundliPayload): Promise<void> {
    this.saving.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
      const previousActive = this.kundlis.activeId();
      if (!previousActive) {
        this.error.set('Select your own profile before checking compatibility.');
        return;
      }
      // Adding a person to compare with must not switch whose app this is.
      const created = await this.kundlis.create(payload, { activate: false });
      await this.router.navigate(['/m', 'compat', 'results'], { queryParams: { partner: created.id } });
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.saving.set(false);
    }
  }
}
