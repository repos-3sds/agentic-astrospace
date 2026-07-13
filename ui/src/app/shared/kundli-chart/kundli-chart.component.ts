import { Component, computed, input } from '@angular/core';

import { SIGN_ORDER, signMeta } from '../../core/glyphs';
import { VargaChart } from '../../core/models';

export type KundliChartStyle = 'north' | 'south';

interface HousePoint {
  house: number;
  x: number;
  y: number;
}

interface HouseView extends HousePoint {
  sign: string;
  signLabel: string;
  signColor: string;
  entries: string[];
}

interface SouthCell {
  sign: string;
  signLabel: string;
  signColor: string;
  house: number;
  x: number;
  y: number;
  entries: string[];
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

@Component({
  selector: 'app-kundli-chart',
  templateUrl: './kundli-chart.component.html',
  styleUrl: './kundli-chart.component.scss',
})
export class KundliChartComponent {
  readonly chart = input<VargaChart | null>(null);
  readonly chartStyle = input<KundliChartStyle>('north');

  protected readonly houses = computed<HouseView[]>(() => {
    const chart = this.chart();
    if (!chart) return [];

    const planetsByHouse = new Map<number, string[]>();
    for (const [planet, position] of Object.entries(chart.planets)) {
      const house = position.house;
      const label = this.planetShortName(planet);
      planetsByHouse.set(house, [...(planetsByHouse.get(house) ?? []), label]);
    }

    const lagnaIndex = SIGN_ORDER.indexOf(chart.lagna.sign);
    return HOUSE_POINTS.map((point) => {
      const sign = this.signForHouse(lagnaIndex, chart.lagna.sign, point.house);
      const meta = signMeta(sign);
      const planets = point.house === 1
        ? ['Lagna', ...(planetsByHouse.get(point.house) ?? [])]
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

    const planetsBySign = new Map<string, string[]>();
    for (const [planet, position] of Object.entries(chart.planets)) {
      const label = this.planetShortName(planet);
      planetsBySign.set(position.sign, [...(planetsBySign.get(position.sign) ?? []), label]);
    }

    const lagnaIndex = SIGN_ORDER.indexOf(chart.lagna.sign);
    return SIGN_ORDER.map((sign) => {
      const point = SOUTH_SIGN_POINTS[sign];
      const meta = signMeta(sign);
      const planets = sign === chart.lagna.sign
        ? ['Lagna', ...(planetsBySign.get(sign) ?? [])]
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
