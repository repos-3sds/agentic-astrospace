import { Component, computed, input } from '@angular/core';

import { SIGN_ORDER, signMeta } from '../../core/glyphs';
import { PlanetConditionAnnotation, PlanetConditionCode, VargaChart } from '../../core/models';

export type KundliChartStyle = 'north' | 'south' | 'eastern';

interface HousePoint {
  house: number;
  x: number;
  y: number;
}

interface HouseView extends HousePoint {
  sign: string;
  signLabel: string;
  signColor: string;
  entries: PlanetEntry[];
}

interface SouthCell {
  sign: string;
  signLabel: string;
  signColor: string;
  house: number;
  x: number;
  y: number;
  entries: PlanetEntry[];
}

interface EasternCell extends SouthCell {
  labelX: number;
  labelY: number;
  align: 'start' | 'middle' | 'end';
}

interface PlanetEntry {
  key: string;
  label: string;
  annotations: PlanetConditionAnnotation[];
}

const HOUSE_POINTS: HousePoint[] = [
  { house: 1, x: 200, y: 82 },
  { house: 2, x: 112, y: 54 },
  { house: 3, x: 55, y: 112 },
  { house: 4, x: 86, y: 200 },
  { house: 5, x: 55, y: 288 },
  { house: 6, x: 112, y: 346 },
  { house: 7, x: 200, y: 318 },
  { house: 8, x: 288, y: 346 },
  { house: 9, x: 345, y: 288 },
  { house: 10, x: 314, y: 200 },
  { house: 11, x: 345, y: 112 },
  { house: 12, x: 288, y: 54 },
];

const SOUTH_SIGN_POINTS: Record<string, { col: number; row: number }> = {
  Pisces: { col: 0, row: 0 },
  Aries: { col: 1, row: 0 },
  Taurus: { col: 2, row: 0 },
  Gemini: { col: 3, row: 0 },
  Aquarius: { col: 0, row: 1 },
  Cancer: { col: 3, row: 1 },
  Capricorn: { col: 0, row: 2 },
  Leo: { col: 3, row: 2 },
  Sagittarius: { col: 0, row: 3 },
  Scorpio: { col: 1, row: 3 },
  Libra: { col: 2, row: 3 },
  Virgo: { col: 3, row: 3 },
};

const EASTERN_SIGN_POINTS: Record<string, { x: number; y: number; labelX: number; labelY: number; align: 'start' | 'middle' | 'end' }> = {
  Aries: { x: 32, y: 96, labelX: 12, labelY: 112, align: 'start' },
  Taurus: { x: 150, y: 36, labelX: 142, labelY: 18, align: 'start' },
  Gemini: { x: 276, y: 34, labelX: 272, labelY: 18, align: 'start' },
  Cancer: { x: 328, y: 96, labelX: 388, labelY: 112, align: 'start' },
  Leo: { x: 276, y: 164, labelX: 272, labelY: 150, align: 'start' },
  Virgo: { x: 296, y: 278, labelX: 272, labelY: 284, align: 'start' },
  Libra: { x: 294, y: 348, labelX: 388, labelY: 382, align: 'start' },
  Scorpio: { x: 150, y: 284, labelX: 142, labelY: 284, align: 'start' },
  Sagittarius: { x: 74, y: 348, labelX: 12, labelY: 382, align: 'end' },
  Capricorn: { x: 32, y: 278, labelX: 12, labelY: 284, align: 'start' },
  Aquarius: { x: 28, y: 164, labelX: 12, labelY: 150, align: 'start' },
  Pisces: { x: 92, y: 34, labelX: 12, labelY: 18, align: 'end' },
};

@Component({
  selector: 'app-kundli-chart',
  templateUrl: './kundli-chart.component.html',
  styleUrl: './kundli-chart.component.scss',
})
export class KundliChartComponent {
  readonly chart = input<VargaChart | null>(null);
  readonly chartStyle = input<KundliChartStyle>('north');
  readonly annotations = input<Record<string, PlanetConditionAnnotation[]>>({});

  protected readonly houses = computed<HouseView[]>(() => {
    const chart = this.chart();
    if (!chart) return [];

    const planetsByHouse = new Map<number, PlanetEntry[]>();
    for (const [planet, position] of Object.entries(chart.planets)) {
      const house = position.house;
      planetsByHouse.set(house, [...(planetsByHouse.get(house) ?? []), this.entryForPlanet(planet)]);
    }

    const lagnaIndex = SIGN_ORDER.indexOf(chart.lagna.sign);
    return HOUSE_POINTS.map((point) => {
      const sign = this.signForHouse(lagnaIndex, chart.lagna.sign, point.house);
      const meta = signMeta(sign);
      const planets = point.house === 1
        ? [this.lagnaEntry(), ...(planetsByHouse.get(point.house) ?? [])]
        : (planetsByHouse.get(point.house) ?? []);
      return {
        ...point,
        sign,
        signLabel: this.signShortName(sign),
        signColor: meta.color,
        entries: planets,
      };
    });
  });

  protected readonly southCells = computed<SouthCell[]>(() => {
    const chart = this.chart();
    if (!chart) return [];

    const planetsBySign = new Map<string, PlanetEntry[]>();
    for (const [planet, position] of Object.entries(chart.planets)) {
      planetsBySign.set(position.sign, [...(planetsBySign.get(position.sign) ?? []), this.entryForPlanet(planet)]);
    }

    const lagnaIndex = SIGN_ORDER.indexOf(chart.lagna.sign);
    return SIGN_ORDER.map((sign) => {
      const point = SOUTH_SIGN_POINTS[sign];
      const meta = signMeta(sign);
      const planets = sign === chart.lagna.sign
        ? [this.lagnaEntry(), ...(planetsBySign.get(sign) ?? [])]
        : (planetsBySign.get(sign) ?? []);
      return {
        sign,
        signLabel: this.signShortName(sign),
        signColor: meta.color,
        house: this.houseForSign(lagnaIndex, sign),
        x: point.col * 100,
        y: point.row * 100,
        entries: planets,
      };
    });
  });

  protected readonly easternCells = computed<EasternCell[]>(() => {
    const chart = this.chart();
    if (!chart) return [];

    const planetsBySign = this.planetsBySign(chart);
    const lagnaIndex = SIGN_ORDER.indexOf(chart.lagna.sign);
    return SIGN_ORDER.map((sign) => {
      const point = EASTERN_SIGN_POINTS[sign];
      const meta = signMeta(sign);
      const planets = sign === chart.lagna.sign
        ? [this.lagnaEntry('As'), ...(planetsBySign.get(sign) ?? [])]
        : (planetsBySign.get(sign) ?? []);
      return {
        sign,
        signLabel: this.signShortName(sign),
        signColor: meta.color,
        house: this.houseForSign(lagnaIndex, sign),
        x: point.x,
        y: point.y,
        labelX: point.labelX,
        labelY: point.labelY,
        align: point.align,
        entries: planets,
      };
    });
  });

  private planetsBySign(chart: VargaChart): Map<string, PlanetEntry[]> {
    const planetsBySign = new Map<string, PlanetEntry[]>();
    for (const [planet, position] of Object.entries(chart.planets)) {
      planetsBySign.set(position.sign, [...(planetsBySign.get(position.sign) ?? []), this.entryForPlanet(planet)]);
    }
    return planetsBySign;
  }

  private signForHouse(lagnaIndex: number, fallback: string, house: number): string {
    if (lagnaIndex < 0) return fallback;
    return SIGN_ORDER[(lagnaIndex + house - 1) % SIGN_ORDER.length];
  }

  private houseForSign(lagnaIndex: number, sign: string): number {
    const signIndex = SIGN_ORDER.indexOf(sign);
    if (lagnaIndex < 0 || signIndex < 0) return 0;
    return ((signIndex - lagnaIndex + SIGN_ORDER.length) % SIGN_ORDER.length) + 1;
  }

  private planetShortName(planet: string): string {
    const names: Record<string, string> = {
      Sun: 'Su',
      Moon: 'Mo',
      Mercury: 'Me',
      Venus: 'Ve',
      Mars: 'Ma',
      Jupiter: 'Ju',
      Saturn: 'Sa',
      Rahu: 'Ra',
      Ketu: 'Ke',
      Uranus: 'Ur',
      Neptune: 'Ne',
      Pluto: 'Pl',
    };
    return names[planet] ?? planet.slice(0, 2);
  }

  private entryForPlanet(planet: string): PlanetEntry {
    const chartPlanet = this.chart()?.planets[planet];
    const automatic: PlanetConditionAnnotation[] = [];
    if (chartPlanet?.retrograde) {
      automatic.push({ code: 'retrograde', symbol: '↺', label: 'Retrograde', tone: 'neutral' });
    }
    if (chartPlanet?.vargottama) {
      automatic.push({ code: 'vargottama', symbol: '✦', label: 'Vargottama', tone: 'good' });
    }
    return {
      key: planet,
      label: this.planetShortName(planet),
      annotations: this.mergeAnnotations(automatic, this.annotations()[planet] ?? []),
    };
  }

  private lagnaEntry(label = 'Lagna'): PlanetEntry {
    return { key: 'Lagna', label, annotations: [] };
  }

  private mergeAnnotations(
    first: PlanetConditionAnnotation[],
    second: PlanetConditionAnnotation[],
  ): PlanetConditionAnnotation[] {
    const seen = new Set<PlanetConditionCode>();
    return [...first, ...second].filter((item) => {
      if (seen.has(item.code)) return false;
      seen.add(item.code);
      return true;
    });
  }

  private signShortName(sign: string): string {
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
}
