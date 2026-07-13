import { Component, computed, effect, inject, signal } from '@angular/core';
import { Skeleton } from 'primeng/skeleton';

import { KundliStore } from '../../../core/kundli.store';
import { AshtakavargaPayload } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { SectionCardComponent } from '../../../shared/section-card/section-card.component';

@Component({
  selector: 'app-ashtakavarga-tab',
  imports: [Skeleton, SectionCardComponent],
  templateUrl: './ashtakavarga-tab.component.html',
  styleUrl: './ashtakavarga-tab.component.scss',
})
export class AshtakavargaTabComponent {
  private store = inject(KundliStore);
  private vedic = inject(VedicService);

  protected readonly modes = [
    { id: 'sav', label: 'SAV' },
    { id: 'bav', label: 'BAV' },
    { id: 'shodhana', label: 'Shodhana' },
    { id: 'pinda', label: 'Pinda' },
    { id: 'prastara', label: 'Prastara' },
  ] as const;
  protected readonly mode = signal<(typeof this.modes)[number]['id']>('sav');
  protected readonly selectedPlanet = signal('Sun');
  protected readonly data = signal<AshtakavargaPayload | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly loading = computed(() => !this.data() && !this.error());

  protected readonly strongest = computed(() =>
    [...(this.data()?.signs ?? [])].sort((a, b) => b.sav - a.sav).slice(0, 3),
  );
  protected readonly weakest = computed(() =>
    [...(this.data()?.signs ?? [])].sort((a, b) => a.sav - b.sav).slice(0, 3),
  );
  protected readonly selectedShodhana = computed(() => this.data()?.shodhana?.[this.selectedPlanet()] ?? null);
  protected readonly selectedPrastara = computed(() => this.data()?.prastara?.[this.selectedPlanet()] ?? null);
  protected readonly selectedPinda = computed(() => this.data()?.pinda?.[this.selectedPlanet()] ?? null);

  constructor() {
    effect(() => {
      const id = this.store.activeId();
      this.data.set(null);
      this.error.set(null);
      if (!id) return;
      this.vedic
        .ashtakavarga(id)
        .then((d) => this.data.set(d))
        .catch((e) => this.error.set((e as Error).message));
    });
  }

  protected heat(score: number): number {
    return Math.min(1, Math.max(0, (score - 18) / 22));
  }

  protected planetTotal(planet: string): number {
    return this.data()?.totals.bav[planet] ?? 0;
  }

  protected sourceTotal(scores: number[] | undefined): number {
    return scores?.reduce((total, score) => total + score, 0) ?? 0;
  }
}
