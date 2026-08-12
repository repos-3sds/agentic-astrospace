import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { VedicAll } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { BirthDetailsCardComponent } from './birth-details-card.component';

/**
 * The practitioner's birth-details screen — everything stated, nothing assumed.
 *
 * A practitioner cross-checking this app against their own software needs the
 * inputs, not just the conclusions: coordinates, time zone, and above all the
 * ayanamsha and its exact value, because that is the usual reason two programs
 * disagree about a lagna. Showing the conclusions without the inputs is what
 * makes a chart unfalsifiable.
 */
@Component({
  selector: 'as-birth-details-screen',
  standalone: true,
  imports: [RouterLink, BirthDetailsCardComponent],
  templateUrl: './birth-details-screen.component.html',
  styleUrl: './birth-details-screen.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BirthDetailsScreenComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);

  protected readonly chart = signal<VedicAll | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly personName = computed(() => this.kundlis.active()?.name ?? null);

  constructor() {
    void this.load();
  }

  protected async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
      const profile = this.kundlis.active();
      if (!profile) throw new Error('Select a profile to see its birth details.');
      // `cachedAll` first: Today already warms this, so the screen usually opens
      // with no request at all.
      this.chart.set(this.vedic.cachedAll(profile.id) ?? (await this.vedic.all(profile.id)));
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }
}
