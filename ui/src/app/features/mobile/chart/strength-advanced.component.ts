import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { map } from 'rxjs';
import { SIGN_ORDER } from '../../../core/glyphs';
import { KundliStore } from '../../../core/kundli.store';
import { AshtakavargaPayload, CharaDashaPayload, VedicAll, VimshopakaBalaPayload } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { SIGN_SHORT } from './mobile-chart-data';

type StrengthTab = 'shadbala' | 'ashtakavarga' | 'jaimini' | 'vimshopaka';

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
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  readonly tab = signal<StrengthTab>('shadbala');
  readonly avPlanet = signal('SAV');
  readonly vimshopakaScheme = signal('shodashavarga');
  protected readonly data = signal<VedicAll | null>(null);
  protected readonly ashtakavarga = signal<AshtakavargaPayload | null>(null);
  protected readonly vimshopaka = signal<VimshopakaBalaPayload | null>(null);
  protected readonly charaDasha = signal<CharaDashaPayload | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  private readonly requestedTab = toSignal(
    this.route.queryParamMap.pipe(
      map((params) => this.validTab(params.get('tab'))),
    ),
    { initialValue: this.validTab(this.route.snapshot.queryParamMap.get('tab')) },
  );

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
  readonly strongestHouse = computed(() =>
    [...this.displayedHouses()].sort((a, b) => b.value - a.value)[0] ?? null,
  );
  readonly weakestHouse = computed(() =>
    [...this.displayedHouses()].sort((a, b) => a.value - b.value)[0] ?? null,
  );
  readonly ashtakavargaMeaning = computed(() => {
    const strong = this.strongestHouse();
    const weak = this.weakestHouse();
    if (!strong || !weak) return 'Ashtakavarga shows where effort tends to meet support and where more patience is needed.';
    if (this.avPlanet() === 'SAV') {
      return `The strongest support is around house ${strong.house} (${strong.sign}), so that life area usually responds better to effort. House ${weak.house} (${weak.sign}) is not “bad”; it simply asks for more preparation, patience, and realistic timing.`;
    }
    return `${this.avPlanet()} gives more support to ${strong.sign} matters and asks for care around ${weak.sign} matters. Read this as that planet's personal support map, not as a final prediction by itself.`;
  });
  readonly shadbalaMeaning = computed(() => {
    const rows = this.strengths();
    const strong = [...rows].sort((a, b) => b.score - a.score)[0];
    const weak = [...rows].sort((a, b) => a.score - b.score)[0];
    if (!strong || !weak) return 'Shadbala compares each planet with its classical minimum so you can see which influences have more operating strength.';
    return `${strong.name} has the clearest operating strength in this chart. ${weak.name} needs more conscious handling, so its topics should be approached with steadiness rather than force.`;
  });
  readonly jaiminiMeaning = computed(() => {
    const atmakaraka = this.karakas().find((row) => String(row[0]).toLowerCase().includes('atma'));
    const arudha = this.data()?.jaimini?.arudha_lagna?.sign_name;
    const parts = [
      atmakaraka ? `${atmakaraka[1]} carries the Atmakaraka role, pointing to the soul-level lesson that keeps repeating.` : 'Chara karakas show role-based significators rather than fixed planet meanings.',
      arudha ? `Arudha Lagna in ${arudha} shows how the chart tends to be perceived by the world.` : 'Arudha padas show reflected image: how a life area appears, not only what it privately is.',
    ];
    return parts.join(' ');
  });

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
      ['Bhrigu Bindu', 'Karmic pressure point', data?.bhrigu_bindu ? `${data.bhrigu_bindu.sign_name} ${data.bhrigu_bindu.dms}` : '—'],
      ['Indu Lagna', 'Wealth potential lens', data?.indu_lagna ? `${data.indu_lagna.sign_name} ${data.indu_lagna.dms}` : '—'],
    ];
  });
  readonly charaRows = computed(() => (this.charaDasha()?.mahadashas ?? []).map((period) => [
    period.sign_name,
    period.lord,
    `${this.dateLabel(period.start)}–${this.dateLabel(period.end)}`,
    period.active ? 'ACTIVE' : `${period.years}y`,
  ]));
  readonly activeChara = computed(() => {
    const current = this.charaDasha()?.current;
    const maha = current?.mahadasha;
    const antar = current?.antardasha;
    if (!maha) return 'No active Chara Dasha returned for the current date.';
    return `${maha.sign_name} mahadasha${antar ? ` with ${antar.sign_name} antardasha` : ''}. This is a Jaimini sign-period lens, not a replacement for Vimshottari.`;
  });
  readonly vimshopakaRows = computed(() =>
    Object.entries(this.vimshopaka()?.planets ?? {})
      .map(([planet, row]) => ({ planet, ...row }))
      .sort((a, b) => b.score - a.score),
  );
  readonly vimshopakaMeaning = computed(() => {
    const rows = this.vimshopakaRows();
    const strongest = rows[0];
    const weakest = rows[rows.length - 1];
    if (!strongest || !weakest) return 'Vimshopaka Bala shows how consistently a planet holds dignity across divisional charts.';
    return `${strongest.planet} is most consistent across the selected varga scheme. ${weakest.planet} needs the most cross-chart caution; read its promises only after checking the relevant divisional chart.`;
  });

  constructor() {
    effect(() => {
      const tab = this.requestedTab();
      if (tab && tab !== this.tab()) this.tab.set(tab);
    });
    effect(() => {
      const activeId = this.kundlis.activeId();
      void this.load(activeId);
    });
  }

  protected selectTab(tab: StrengthTab): void {
    this.tab.set(tab);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { tab },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  protected selectVimshopakaScheme(scheme: string): void {
    this.vimshopakaScheme.set(scheme);
    const activeId = this.kundlis.activeId();
    if (activeId) void this.loadVimshopaka(activeId, scheme);
  }

  protected retry(): void {
    void this.load(this.kundlis.activeId());
  }

  private validTab(value: string | null): StrengthTab | null {
    return value === 'shadbala' || value === 'ashtakavarga' || value === 'jaimini' || value === 'vimshopaka'
      ? value
      : null;
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
        this.vimshopaka.set(null);
        this.charaDasha.set(null);
        return;
      }
      const [all, vimshopaka, charaDasha] = await Promise.all([
        this.vedic.all(activeId),
        this.vedic.vimshopakaBala(activeId, this.vimshopakaScheme()).catch(() => null),
        this.vedic.charaDasha(activeId).catch(() => null),
      ]);
      this.data.set(all);
      this.ashtakavarga.set(all.ashtakavarga ?? await this.vedic.ashtakavarga(activeId));
      this.vimshopaka.set(vimshopaka);
      this.charaDasha.set(charaDasha);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  private async loadVimshopaka(activeId: string, scheme: string): Promise<void> {
    try {
      this.vimshopaka.set(await this.vedic.vimshopakaBala(activeId, scheme));
    } catch {
      this.vimshopaka.set(null);
    }
  }

  private dateLabel(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value || '—';
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  }
}
