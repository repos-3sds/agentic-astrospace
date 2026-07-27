import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { VedicService } from '../../../core/vedic.service';
import { VedicAll } from '../../../core/models';

type ReferenceMode = 'home' | 'avkahada' | 'grahas' | 'ashtakavarga' | 'favourable';

@Component({
  selector: 'as-chart-reference',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './reference.component.html',
  styleUrl: './reference.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReferenceComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  protected readonly mode = inject(ActivatedRoute).snapshot.data['referenceMode'] as ReferenceMode;
  protected readonly data = signal<VedicAll | null>(null);
  protected readonly ashtakavarga = signal<unknown>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  protected readonly title = computed(() => ({
    home: 'Reference', avkahada: 'Avkahada chakra', grahas: 'Graha positions',
    ashtakavarga: 'Ashtakavarga tables', favourable: 'Favourable points',
  })[this.mode]);
  protected readonly subtitle = computed(() => ({
    home: 'Classical tables and birth constants — the practitioner’s workbench.',
    avkahada: 'Your birth constants, from the Moon’s nakshatra',
    grahas: 'Sidereal positions, nakshatra-pada and conditions',
    ashtakavarga: 'Bindu tables computed from your chart',
    favourable: 'Your birth-constant signature — steady across your life.',
  })[this.mode]);
  protected readonly homeCards = [
    { label: 'Avkahada & Ghatak', detail: 'Varna, vashya, yoni, gana, nadi, tatwa · ghatak points', route: 'avkahada' },
    { label: 'Graha positions & conditions', detail: 'Degrees, nakshatra-pada, dignity and motion', route: 'grahas' },
    { label: 'Ashtakavarga tables', detail: 'Planet and sign bindu working', route: 'ashtakavarga' },
    { label: 'Favourable points', detail: 'Birth-constant colours, numbers and directions', route: 'favourable' },
  ];

  protected readonly simpleRows = computed(() => {
    const data = this.data();
    const source = this.mode === 'avkahada'
      ? { ...(data?.avkahada ?? {}), ...(data?.ghatak ?? {}) }
      : this.mode === 'favourable' ? data?.favourable ?? {} : {};
    return this.flatten(source);
  });
  protected readonly planets = computed(() => Object.entries(this.data()?.planets ?? {}));
  protected readonly ashtaRows = computed(() => this.flatten(this.ashtakavarga() ?? {}));

  constructor() { if (this.mode !== 'home') void this.load(); else this.loading.set(false); }

  protected async load(): Promise<void> {
    this.loading.set(true); this.error.set(null);
    try {
      await this.kundlis.load();
      const profile = this.kundlis.active();
      if (!profile) throw new Error('Select a profile to open reference tables.');
      if (this.mode === 'ashtakavarga') {
        this.ashtakavarga.set(await this.vedic.ashtakavarga(profile.id));
      } else {
        this.data.set(await this.vedic.all(profile.id));
      }
    } catch (error) {
      this.error.set((error as Error).message);
    } finally { this.loading.set(false); }
  }

  private flatten(value: unknown, prefix = ''): { label: string; value: string }[] {
    if (!value || typeof value !== 'object') return [];
    const rows: { label: string; value: string }[] = [];
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      const label = prefix ? `${prefix} · ${key}` : key;
      if (item !== null && typeof item === 'object') rows.push(...this.flatten(item, label));
      else rows.push({ label: label.replaceAll('_', ' '), value: String(item ?? '—') });
    }
    return rows.slice(0, 120);
  }
}
