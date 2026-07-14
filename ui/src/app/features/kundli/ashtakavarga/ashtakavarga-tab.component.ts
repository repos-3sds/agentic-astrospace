import { Component, computed, effect, inject, signal } from '@angular/core';
import { Skeleton } from 'primeng/skeleton';

import { SIGN_ORDER, signMeta } from '../../../core/glyphs';
import { KundliStore } from '../../../core/kundli.store';
import { AshtakavargaPayload } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { SectionCardComponent } from '../../../shared/section-card/section-card.component';

interface AvChartCell {
  sign: string;
  signLabel: string;
  signColor: string;
  value: number;
  col: number;
  row: number;
  heat: number;
}

const SOUTH_SIGN_POINTS: Record<string, { col: number; row: number }> = {
  Pisces: { col: 1, row: 1 },
  Aries: { col: 2, row: 1 },
  Taurus: { col: 3, row: 1 },
  Gemini: { col: 4, row: 1 },
  Aquarius: { col: 1, row: 2 },
  Cancer: { col: 4, row: 2 },
  Capricorn: { col: 1, row: 3 },
  Leo: { col: 4, row: 3 },
  Sagittarius: { col: 1, row: 4 },
  Scorpio: { col: 2, row: 4 },
  Libra: { col: 3, row: 4 },
  Virgo: { col: 4, row: 4 },
};

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
  protected readonly savCells = computed(() => this.chartCells(this.data()?.sav ?? [], 'sav'));
  protected readonly bavCells = computed(() => this.chartCells(this.data()?.bav[this.selectedPlanet()] ?? [], 'bav'));
  protected readonly shodhanaRawCells = computed(() => this.chartCells(this.data()?.bav[this.selectedPlanet()] ?? [], 'bav'));
  protected readonly shodhanaTrikonaCells = computed(() => this.chartCells(this.selectedShodhana()?.trikona ?? [], 'bav'));
  protected readonly shodhanaEkadhipatyaCells = computed(() => this.chartCells(this.selectedShodhana()?.ekadhipatya ?? [], 'bav'));

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

  protected heat(score: number, kind: 'sav' | 'bav' = 'sav'): number {
    if (kind === 'bav') return Math.min(1, Math.max(0, score / 8));
    return Math.min(1, Math.max(0, (score - 18) / 22));
  }

  protected planetTotal(planet: string): number {
    return this.data()?.totals.bav[planet] ?? 0;
  }

  protected sourceTotal(scores: number[] | undefined): number {
    return scores?.reduce((total, score) => total + score, 0) ?? 0;
  }

  protected signShortName(sign: string): string {
    const names: Record<string, string> = {
      Aries: 'Ari',
      Taurus: 'Tau',
      Gemini: 'Gem',
      Cancer: 'Can',
      Leo: 'Leo',
      Virgo: 'Vir',
      Libra: 'Lib',
      Scorpio: 'Sco',
      Sagittarius: 'Sag',
      Capricorn: 'Cap',
      Aquarius: 'Aqu',
      Pisces: 'Pis',
    };
    return names[sign] ?? sign.slice(0, 3);
  }

  private chartCells(scores: number[], kind: 'sav' | 'bav'): AvChartCell[] {
    if (!scores.length) return [];
    return SIGN_ORDER.map((sign, index) => {
      const point = SOUTH_SIGN_POINTS[sign];
      const meta = signMeta(sign);
      const value = scores[index] ?? 0;
      return {
        sign,
        signLabel: this.signShortName(sign),
        signColor: meta.color,
        value,
        col: point.col,
        row: point.row,
        heat: this.heat(value, kind),
      };
    });
  }
}
