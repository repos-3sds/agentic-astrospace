import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { DashaPayload, VedicAll } from '../../../core/models';
import { PlanGateService } from '../../../core/plan-gate.service';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { buildChartAdapter } from '../chart/mobile-chart-data';
import { monthYear } from '../format-date';
import { ProfileSwitcherComponent } from '../profile-switcher/profile-switcher.component';

type Tone = 'accent' | 'good' | 'warn' | 'muted';

interface ExploreTile {
  id: string;
  label: string;
  detail: string;
  tone: Tone;
  icon: string;
  route: string[];
  /** The plan flag that opens it fully; a tile without one is free. */
  gate?: string;
  /** Free shows part of it, so the tile says what is included rather than locking. */
  partial?: string;
}

/**
 * The Explore tab in Guided and Balanced (Hawk, 2026-10-16). It combines
 * three designs Hawk picked: the Practitioner board's greeting and live
 * tiles, Guided Explore's featured card, and the cosmic snapshot from the
 * Your Chart design. Settings sits behind the gear.
 *
 * Tiles a plan does not include stay listed with a Plus mark, so the reader
 * can see what there is, and open to a screen that says what Plus adds.
 */
@Component({
  selector: 'as-explore-menu',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ProfileSwitcherComponent, RouterLink],
  templateUrl: './explore-menu.component.html',
  styleUrl: './explore-menu.component.scss',
})
export class ExploreMenuComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  private readonly gate = inject(PlanGateService);
  protected readonly preferences = inject(PreferencesService);

  protected readonly profileSwitcherOpen = signal(false);
  private readonly chart = signal<VedicAll | null>(null);
  private readonly dashas = signal<DashaPayload | null>(null);

  protected readonly profile = computed(() => {
    const k = this.kundlis.active();
    const owner = this.kundlis.owner();
    const name = k?.name ?? 'Choose a person';
    const first = name.split(' ')[0];
    return {
      first: owner?.name.split(' ')[0] ?? first,
      initial: name.slice(0, 1).toUpperCase(),
      // The greeting is for the account holder; this says whose chart is open.
      viewing: owner && k && owner.id !== k.id ? first : null,
    };
  });

  /** Sun, Moon and rising from the computed chart, as Your chart shows them. */
  protected readonly snapshot = computed(() => {
    const chart = this.chart();
    const angles = chart ? buildChartAdapter(chart, this.kundlis.active()).angles : [];
    const sign = (label: string) => angles.find((a) => a.label === label)?.sign ?? '—';
    const cells = [
      { label: 'SUN', sign: sign('SUN') },
      { label: 'MOON', sign: sign('MOON') },
      { label: 'RISING', sign: sign('ASCENDANT') },
    ];
    return {
      ready: !!chart,
      headline: chart ? `${cells[0].sign} Sun, ${cells[1].sign} Moon, ${cells[2].sign} rising.` : 'Your chart is loading.',
      cells,
    };
  });

  protected readonly tiles = computed(() => {
    // Read once so the tiles recompute when the plan snapshot arrives.
    this.gate.live();
    const k = this.kundlis.active();
    const chart = this.chart();
    const guided = this.preferences.experienceMode() === 'guided';

    const time = k ? `${String(k.birth_hour).padStart(2, '0')}:${String(k.birth_minute).padStart(2, '0')}` : '';
    const yogas = chart?.yogas?.active_count;
    const doshas = chart?.doshas
      ? [chart.doshas.manglik, chart.doshas.gandanta, chart.doshas.grahan].filter((d) => d?.active).length
      : null;
    const maha = (this.dashas() ?? chart?.dashas)?.current?.mahadasha;

    const rows: ExploreTile[] = [
      { id: 'birth', label: 'Birth details', detail: k ? [k.birth_city, time].filter(Boolean).join(' · ') : 'Date, time and place', tone: 'accent', icon: 'figma-yantra-nav-map-pin', route: ['/m', 'chart', 'birth-details'] },
      {
        id: 'yogas', label: 'Yogas & doshas',
        detail: yogas != null ? `${yogas} yogas · ${doshas ?? 0} ${doshas === 1 ? 'dosha' : 'doshas'} flagged` : 'Strengths and flags',
        tone: 'warn', icon: 'figma-yantra-git-commit', route: ['/m', 'chart', 'yogas'], gate: 'yogas.full', partial: '2 yogas, every dosha',
      },
      {
        id: 'periods', label: guided ? 'Life chapters' : 'Life periods',
        detail: maha?.end ? `${maha.lord} period until ${monthYear(maha.end)}` : 'Your current chapter',
        tone: 'accent', icon: 'figma-yantra-clock', route: guided ? ['/m', 'explore', 'life-chapters'] : ['/m', 'chart', 'periods'],
      },
      { id: 'compat', label: 'Compatibility', detail: 'Gun Milan matching', tone: 'muted', icon: 'explore-compat', route: ['/m', 'compat'], gate: 'compatibility.full', partial: 'Score, 1 a month' },
      { id: 'readings', label: 'Readings', detail: 'Period readings', tone: 'muted', icon: 'figma-yantra-file-text', route: ['/m', 'readings'], gate: 'readings.full' },
      { id: 'remedies', label: 'Remedies', detail: 'Traditional practices', tone: 'good', icon: 'figma-yantra-sun', route: ['/m', 'remedies'], gate: 'remedies.full', partial: '1 practice' },
      { id: 'muhurta', label: 'Muhurtas', detail: 'Find a good time', tone: 'warn', icon: 'figma-yantra-calendar', route: ['/m', 'muhurta'], gate: 'muhurta.full' },
      { id: 'notes', label: 'Notes', detail: 'Your private reflections', tone: 'muted', icon: 'figma-yantra-edit-3', route: ['/m', 'notes'] },
    ];
    return rows.map((row) => {
      const open = !row.gate || this.gate.allows(row.gate);
      return {
        ...row,
        detail: open || !row.partial ? row.detail : row.partial,
        locked: !open && !row.partial,
        partial: !open && !!row.partial,
      };
    });
  });

  constructor() {
    effect(() => {
      const id = this.kundlis.activeId();
      void this.load(id);
    });
  }

  private async load(id: string | null): Promise<void> {
    if (!id) {
      this.chart.set(null);
      this.dashas.set(null);
      return;
    }
    this.dashas.set(null);
    const cached = this.vedic.cachedAll(id);
    this.chart.set(cached);
    try {
      if (!cached) {
        const chart = await this.vedic.all(id);
        if (this.kundlis.activeId() === id) this.chart.set(chart);
      }
      const dashas = await this.vedic.dashas(id);
      if (this.kundlis.activeId() === id) this.dashas.set(dashas);
    } catch {
      // The tiles fall back to plain descriptions; Your chart shows the error.
    }
  }
}
