import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { VedicService } from '../../../core/vedic.service';
import { AshtakavargaPayload, VedicAll } from '../../../core/models';

type ReferenceMode = 'home' | 'avkahada' | 'grahas' | 'ashtakavarga' | 'favourable';

/** One sign's row in the BAV/SAV matrix: each planet's bindus, then the SAV total. */
interface AshtaRow {
  sign: string;
  short: string;
  bindus: number[];
  sav: number;
}

const SIGN_SHORT: Record<string, string> = {
  Aries: 'Ari', Taurus: 'Tau', Gemini: 'Gem', Cancer: 'Can', Leo: 'Leo', Virgo: 'Vir',
  Libra: 'Lib', Scorpio: 'Sco', Sagittarius: 'Sag', Capricorn: 'Cap', Aquarius: 'Aqu', Pisces: 'Pis',
};

const PLANET_SHORT: Record<string, string> = {
  Sun: 'Su', Moon: 'Mo', Mars: 'Ma', Mercury: 'Me', Jupiter: 'Ju', Venus: 'Ve', Saturn: 'Sa',
};

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
  protected readonly ashtakavarga = signal<AshtakavargaPayload | null>(null);
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

  /**
   * Ashtakavarga as the classical matrix: one row per sign, one column per
   * contributing planet (Sun through Saturn), SAV at the end. Until
   * 2026-10-15 this screen flattened the raw payload into "bav · Sun · 0 = 4"
   * rows and never showed a table.
   */
  protected readonly ashtaPlanets = computed(() => this.ashtakavarga()?.planets ?? []);
  protected readonly ashtaPlanetShort = computed(() => this.ashtaPlanets().map((planet) => PLANET_SHORT[planet] ?? planet.slice(0, 2)));
  protected readonly ashtaRows = computed<AshtaRow[]>(() => {
    const data = this.ashtakavarga();
    if (!data?.signs?.length) return [];
    return data.signs.map((row) => ({
      sign: row.sign,
      short: SIGN_SHORT[row.sign] ?? row.sign.slice(0, 3),
      bindus: data.planets.map((planet) => row.bav[planet] ?? 0),
      sav: row.sav,
    }));
  });
  protected readonly ashtaTotals = computed(() => {
    const data = this.ashtakavarga();
    if (!data) return null;
    return { bav: data.planets.map((planet) => data.totals.bav[planet] ?? 0), sav: data.totals.sav };
  });
  protected readonly ashtaStrongest = computed(() => [...this.ashtaRows()].sort((a, b) => b.sav - a.sav).slice(0, 3));
  protected readonly ashtaWeakest = computed(() => [...this.ashtaRows()].sort((a, b) => a.sav - b.sav).slice(0, 3));
  protected readonly ashtaPinda = computed(() => this.ashtakavarga()?.pinda_rank ?? []);

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

  /** 0..1 heat for a SAV cell: 28 is the classical neutral mark, 18..40 the usual spread. */
  protected savHeat(sav: number): number {
    return Math.min(1, Math.max(0, (sav - 18) / 22));
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
