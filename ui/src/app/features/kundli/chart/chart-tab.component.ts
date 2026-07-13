import { Component, computed, inject, signal } from '@angular/core';

import { planetGlyph, SIGN_ORDER, signMeta } from '../../../core/glyphs';
import { KundliStore } from '../../../core/kundli.store';
import { PlanetPosition } from '../../../core/models';
import { DefListComponent, DefRow } from '../../../shared/def-list/def-list.component';
import { SectionCardComponent } from '../../../shared/section-card/section-card.component';

interface WheelPoint {
  name: string;
  glyph: string;
  sign: string;
  degree: number;
  house: number | string;
  longitude: number;
  retrograde: boolean;
  x: number;
  y: number;
}

interface SignMarker {
  sign: string;
  label: string;
  color: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  labelX: number;
  labelY: number;
}

interface AspectLine {
  a: string;
  b: string;
  type: string;
  orb: number;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  tone: 'soft' | 'hard' | 'neutral';
}

interface BalanceItem {
  label: string;
  value: number;
  pct: number;
}

const ELEMENTS: Record<string, string> = {
  Aries: 'Fire',
  Leo: 'Fire',
  Sagittarius: 'Fire',
  Taurus: 'Earth',
  Virgo: 'Earth',
  Capricorn: 'Earth',
  Gemini: 'Air',
  Libra: 'Air',
  Aquarius: 'Air',
  Cancer: 'Water',
  Scorpio: 'Water',
  Pisces: 'Water',
};

const MODALITIES: Record<string, string> = {
  Aries: 'Cardinal',
  Cancer: 'Cardinal',
  Libra: 'Cardinal',
  Capricorn: 'Cardinal',
  Taurus: 'Fixed',
  Leo: 'Fixed',
  Scorpio: 'Fixed',
  Aquarius: 'Fixed',
  Gemini: 'Mutable',
  Virgo: 'Mutable',
  Sagittarius: 'Mutable',
  Pisces: 'Mutable',
};

const ASPECTS = [
  { type: 'Conjunction', angle: 0, tone: 'neutral' as const },
  { type: 'Sextile', angle: 60, tone: 'soft' as const },
  { type: 'Square', angle: 90, tone: 'hard' as const },
  { type: 'Trine', angle: 120, tone: 'soft' as const },
  { type: 'Opposition', angle: 180, tone: 'hard' as const },
];

@Component({
  selector: 'app-chart-tab',
  imports: [SectionCardComponent, DefListComponent],
  templateUrl: './chart-tab.component.html',
  styleUrl: './chart-tab.component.scss',
})
export class ChartTabComponent {
  private store = inject(KundliStore);

  protected readonly showAspects = signal(true);
  protected readonly showRetrogrades = signal(true);

  protected readonly planets = computed(() => this.store.active()?.chart_data?.planets ?? {});

  protected readonly signMarkers = computed<SignMarker[]>(() =>
    SIGN_ORDER.map((sign, idx) => {
      const line = this.point(idx * 30, 92);
      const outer = this.point(idx * 30, 224);
      const label = this.point(idx * 30 + 15, 202);
      const meta = signMeta(sign);
      return {
        sign,
        label: sign.slice(0, 3),
        color: meta.color,
        x1: line.x,
        y1: line.y,
        x2: outer.x,
        y2: outer.y,
        labelX: label.x,
        labelY: label.y,
      };
    }),
  );

  protected readonly wheelPoints = computed<WheelPoint[]>(() => {
    const rows = Object.entries(this.planets()).map(([name, p]) => {
      const longitude = this.longitude(p);
      return { name, p, longitude };
    });
    rows.sort((a, b) => a.longitude - b.longitude);
    return rows.map(({ name, p, longitude }, idx) => {
      const radius = 158 + (idx % 3) * 15;
      const pos = this.point(longitude, radius);
      return {
        name,
        glyph: planetGlyph(name),
        sign: p.sign,
        degree: p.degree ?? 0,
        house: p.house ?? '-',
        longitude,
        retrograde: !!p.retrograde,
        x: pos.x,
        y: pos.y,
      };
    });
  });

  protected readonly aspectLines = computed<AspectLine[]>(() => {
    const points = this.wheelPoints();
    const lines: AspectLine[] = [];
    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        const a = points[i];
        const b = points[j];
        const diff = this.angleDiff(a.longitude, b.longitude);
        const hit = ASPECTS
          .map((aspect) => ({ ...aspect, orb: Math.abs(diff - aspect.angle) }))
          .filter((aspect) => aspect.orb <= 6)
          .sort((x, y) => x.orb - y.orb)[0];
        if (!hit) continue;
        lines.push({
          a: a.name,
          b: b.name,
          type: hit.type,
          orb: hit.orb,
          x1: a.x,
          y1: a.y,
          x2: b.x,
          y2: b.y,
          tone: hit.tone,
        });
      }
    }
    return lines.sort((a, b) => a.orb - b.orb);
  });

  protected readonly houseRows = computed<DefRow[]>(() => {
    const houses = this.store.active()?.chart_data?.houses ?? {};
    return Object.entries(houses).map(([h, data]) => ({
      label: `House ${h}`,
      value: `${data.sign ?? '-'} · ${data.degree ?? 0}deg`,
    }));
  });

  protected readonly planetRows = computed<DefRow[]>(() =>
    this.wheelPoints().map((p) => ({
      label: p.name,
      value: `${p.sign} ${p.degree.toFixed(2)}deg · H${p.house}${p.retrograde ? ' · R' : ''}`,
    })),
  );

  protected readonly elementBalance = computed<BalanceItem[]>(() =>
    this.balance(['Fire', 'Earth', 'Air', 'Water'], ELEMENTS),
  );

  protected readonly modalityBalance = computed<BalanceItem[]>(() =>
    this.balance(['Cardinal', 'Fixed', 'Mutable'], MODALITIES),
  );

  protected readonly houseFocus = computed<DefRow[]>(() => {
    const byHouse = new Map<string, string[]>();
    for (const p of this.wheelPoints()) {
      const house = String(p.house);
      byHouse.set(house, [...(byHouse.get(house) ?? []), p.name]);
    }
    return [...byHouse.entries()]
      .sort((a, b) => Number(a[0]) - Number(b[0]))
      .map(([house, planets]) => ({ label: `House ${house}`, value: planets.join(', ') }));
  });

  protected readonly retrogrades = computed<DefRow[]>(() =>
    this.wheelPoints()
      .filter((p) => p.retrograde)
      .map((p) => ({ label: p.name, value: `${p.sign} · H${p.house}` })),
  );

  protected readonly dominantElement = computed(() =>
    [...this.elementBalance()].sort((a, b) => b.value - a.value)[0]?.label ?? '—',
  );

  protected toggleAspects(): void {
    this.showAspects.update((v) => !v);
  }

  protected toggleRetrogrades(): void {
    this.showRetrogrades.update((v) => !v);
  }

  private balance(labels: string[], map: Record<string, string>): BalanceItem[] {
    const counts = new Map(labels.map((label) => [label, 0]));
    for (const p of this.wheelPoints()) {
      const key = map[p.sign];
      if (key) counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    const total = Math.max(1, this.wheelPoints().length);
    return labels.map((label) => ({
      label,
      value: counts.get(label) ?? 0,
      pct: ((counts.get(label) ?? 0) / total) * 100,
    }));
  }

  private longitude(p: PlanetPosition): number {
    const signIndex = SIGN_ORDER.indexOf(p.sign);
    if (signIndex < 0) return p.degree ?? 0;
    return signIndex * 30 + (p.degree ?? 0);
  }

  private point(longitude: number, radius: number): { x: number; y: number } {
    const angle = ((longitude - 90) * Math.PI) / 180;
    return {
      x: 250 + radius * Math.cos(angle),
      y: 250 + radius * Math.sin(angle),
    };
  }

  private angleDiff(a: number, b: number): number {
    const diff = Math.abs(a - b) % 360;
    return diff > 180 ? 360 - diff : diff;
  }
}
