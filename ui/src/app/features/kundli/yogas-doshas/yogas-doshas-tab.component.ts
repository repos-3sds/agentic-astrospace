import { Component, computed, effect, inject, signal } from '@angular/core';
import { Skeleton } from 'primeng/skeleton';
import { Tag } from 'primeng/tag';

import { KundliStore } from '../../../core/kundli.store';
import { YogaResult, YogasDoshasPayload } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { SectionCardComponent } from '../../../shared/section-card/section-card.component';

@Component({
  selector: 'app-yogas-doshas-tab',
  imports: [Skeleton, Tag, SectionCardComponent],
  templateUrl: './yogas-doshas-tab.component.html',
  styleUrl: './yogas-doshas-tab.component.scss',
})
export class YogasDoshasTabComponent {
  private store = inject(KundliStore);
  private vedic = inject(VedicService);

  protected readonly data = signal<YogasDoshasPayload | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly loading = computed(() => !this.data() && !this.error());

  protected readonly activeYogas = computed(() => this.data()?.yogas.active ?? []);
  protected readonly cautionYogas = computed(() =>
    this.activeYogas().filter((y) => y.category.toLowerCase().includes('caution')),
  );
  protected readonly supportiveYogas = computed(() =>
    this.activeYogas().filter((y) => !y.category.toLowerCase().includes('caution')),
  );
  protected readonly categories = computed(() =>
    Object.entries(this.data()?.yogas.categories ?? {})
      .sort((a, b) => b[1] - a[1])
      .map(([label, count]) => ({ label, count })),
  );

  constructor() {
    effect(() => {
      const id = this.store.activeId();
      this.data.set(null);
      this.error.set(null);
      if (!id) return;
      this.vedic
        .yogasDoshas(id)
        .then((payload) => this.data.set(payload))
        .catch((e) => this.error.set((e as Error).message));
    });
  }

  protected tagSeverity(yoga: YogaResult): 'success' | 'warn' | 'secondary' {
    if (!yoga.verified) return 'warn';
    return yoga.category.toLowerCase().includes('caution') ? 'warn' : 'success';
  }
}
