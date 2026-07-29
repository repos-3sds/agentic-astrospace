import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { SIGN_ORDER } from '../../../core/glyphs';
import { KundliStore } from '../../../core/kundli.store';
import { AshtakavargaPayload, VedicAll } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { SIGN_SHORT } from './mobile-chart-data';

type StrengthTab = 'shadbala' | 'ashtakavarga' | 'jaimini';

interface PlanetStrength {
  name: string;
  score: number;
  virupa: number;
  minimum: number;
}

interface HouseBindu {
  house: string;
  sign: string;
  short: string;
  value: number;
  x: number;
  y: number;
}

/** Strength & Advanced complete tab flow (Figma 41:149, 60:88, 60:257). */
@Component({
  selector: 'as-strength-advanced',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './strength-advanced.component.html',
  styleUrl: './strength-advanced.component.scss',
})
export class StrengthAdvancedComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  readonly tab = signal<StrengthTab>('shadbala');
  readonly avPlanet = signal('SAV');
  protected readonly data = signal<VedicAll | null>(null);
  protected readonly ashtakavarga = signal<AshtakavargaPayload | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  readonly strengths = computed<PlanetStrength[]>(() => {
    const classical = this.data()?.shadbala?.classical;
    if (classical?.ranking?.length) {
      return classical.ranking.map((row) => ({
        name: row.planet,
        score: Math.round(row.ratio * 100),
        virupa: Math.round(row.rupas * 60),
        minimum: Math.round((classical.required_minima_rupas?.[row.planet] ?? (row.sufficient ? row.rupas / Math.max(row.ratio, 0.01) : row.rupas)) * 60),
      }));
    }
    return (this.data()?.shadbala?.ranking ?? []).map((row) => ({
      name: row.planet,
      score: Math.round(row.score),
      virupa: Math.round(row.score),
      minimum: 100,
    }));
  });

  readonly planets = computed(() => ['SAV', ...(this.ashtakavarga()?.planets ?? [])]);
  readonly houses = computed<HouseBindu[]>(() => {
    const values = this.avPlanet() === 'SAV'
      ? this.ashtakavarga()?.sav ?? []
      : this.ashtakavarga()?.bav?.[this.avPlanet()] ?? [];
    const anchors = [
      { x: 50, y: 10 }, { x: 79, y: 7 }, { x: 93, y: 22 }, { x: 88, y: 50 },
      { x: 93, y: 78 }, { x: 78, y: 93 }, { x: 50, y: 88 }, { x: 22, y: 93 },
      { x: 7, y: 78 }, { x: 12, y: 50 }, { x: 21, y: 7 }, { x: 7, y: 21 },
    ];
    return SIGN_ORDER.map((sign, index) => ({
      house: `${index + 1}`,
      sign,
      short: SIGN_SHORT[sign] ?? sign.slice(0, 2),
      value: values[index] ?? 0,
      x: anchors[index].x,
      y: anchors[index].y,
    }));
  });
  readonly displayedHouses = computed(() => {
    return this.houses();
  });
  // Always summed from what is on screen, never asserted. A total that is
  // stated independently of the cells is a total that can contradict them —
  // and on a screen whose whole claim is "computed, not conjured", a header
  // disagreeing with the grid beneath it is the worst possible bug.
  readonly totalBindus = computed(() =>
    this.displayedHouses().reduce((total, house) => total + house.value, 0),
  );

  readonly karakas = computed(() =>
    (this.data()?.jaimini?.chara_karakas?.ordered ?? []).map((row) => [
      row.karaka,
      `${row.planet}${row.code ? ` (${row.code})` : ''}`,
      `${row.degree_in_sign?.toFixed?.(2) ?? row.effective_degree?.toFixed?.(2) ?? '—'} deg`,
    ]),
  );
  readonly arudhas = computed(() => {
    const jaimini = this.data()?.jaimini;
    const padas = jaimini?.arudha_padas?.padas ?? {};
    return [
      ['A1 · LAGNA', jaimini?.arudha_lagna?.sign_name ?? '—'],
      ['UPAPADA', jaimini?.upapada?.sign_name ?? '—'],
      ...Object.entries(padas).slice(0, 6).map(([key, row]) => [key, row.sign_name]),
    ];
  });
  readonly specialLagnas = computed(() => {
    const data = this.data()?.special_lagnas;
    return [
      ['Bhava Lagna', 'Body & circumstance', data?.bhava_lagna ? `${data.bhava_lagna.sign_name} ${data.bhava_lagna.dms}` : '—'],
      ['Hora Lagna', 'Wealth & resources', data?.hora_lagna ? `${data.hora_lagna.sign_name} ${data.hora_lagna.dms}` : '—'],
      ['Ghati Lagna', 'Power & position', data?.ghati_lagna ? `${data.ghati_lagna.sign_name} ${data.ghati_lagna.dms}` : '—'],
    ];
  });

  constructor() {
    effect(() => {
      const activeId = this.kundlis.activeId();
      void this.load(activeId);
    });
  }

  protected retry(): void {
    void this.load(this.kundlis.activeId());
  }

  private async load(expectedActiveId: string | null): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
      const activeId = this.kundlis.activeId();
      if (expectedActiveId && activeId !== expectedActiveId) return;
      if (!activeId) {
        this.data.set(null);
        this.ashtakavarga.set(null);
        return;
      }
      const all = await this.vedic.all(activeId);
      this.data.set(all);
      this.ashtakavarga.set(all.ashtakavarga ?? await this.vedic.ashtakavarga(activeId));
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }
}
