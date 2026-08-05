import { Component, computed, input, output } from '@angular/core';

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
  labelAlign: 'start' | 'middle' | 'end';
  planetAlign: 'start' | 'middle' | 'end';
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

/**
 * Eastern chart geometry. Grid: 400×400, thirds at 133.33/266.67; corner
 * cells split by diagonals through the outer corners (TL/BR on x=y-style
 * lines, TR/BL on x+y=400-style lines).
 *
 * Per zone: (x, y) anchors the planet stack — the stack is VERTICALLY
 * CENTERED on this point (see easternCells) so stelliums stay inside their
 * triangle; (labelX, labelY) pins the two-line H#/sign label block into the
 * zone's outer pocket, ≥8px inside the viewBox so nothing clips. Anchors
 * were chosen so a 5-planet stack stays on the correct side of each
 * diagonal (planet row height 13, half-width ≈16 at middle anchor).
 */
const EASTERN_SIGN_POINTS: Record<string, {
  x: number;
  y: number;
  labelX: number;
  labelY: number;
  labelAlign: 'start' | 'middle' | 'end';
  planetAlign: 'start' | 'middle' | 'end';
}> = {
  // Top-left corner: Pisces upper-right triangle, Aries lower-left.
  Pisces: { x: 98, y: 60, labelX: 126, labelY: 16, labelAlign: 'end', planetAlign: 'middle' },
  Aries: { x: 36, y: 82, labelX: 8, labelY: 110, labelAlign: 'start', planetAlign: 'middle' },
  // Top edge.
  Taurus: { x: 200, y: 72, labelX: 140, labelY: 16, labelAlign: 'start', planetAlign: 'middle' },
  // Top-right corner: Gemini upper-left triangle, Cancer lower-right.
  Gemini: { x: 302, y: 58, labelX: 274, labelY: 16, labelAlign: 'start', planetAlign: 'middle' },
  Cancer: { x: 364, y: 74, labelX: 392, labelY: 110, labelAlign: 'end', planetAlign: 'middle' },
  // Right edge.
  Leo: { x: 334, y: 205, labelX: 392, labelY: 149, labelAlign: 'end', planetAlign: 'middle' },
  // Bottom-right corner: Virgo upper-right triangle, Libra lower-left.
  Virgo: { x: 366, y: 324, labelX: 392, labelY: 282, labelAlign: 'end', planetAlign: 'middle' },
  Libra: { x: 300, y: 338, labelX: 274, labelY: 370, labelAlign: 'start', planetAlign: 'middle' },
  // Bottom edge.
  Scorpio: { x: 200, y: 330, labelX: 140, labelY: 358, labelAlign: 'start', planetAlign: 'middle' },
  // Bottom-left corner: Sagittarius lower-right triangle, Capricorn upper-left.
  Sagittarius: { x: 100, y: 340, labelX: 126, labelY: 370, labelAlign: 'end', planetAlign: 'middle' },
  Capricorn: { x: 36, y: 324, labelX: 8, labelY: 282, labelAlign: 'start', planetAlign: 'middle' },
  // Left edge.
  Aquarius: { x: 66, y: 205, labelX: 8, labelY: 149, labelAlign: 'start', planetAlign: 'middle' },
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
  readonly interactive = input(false);
  readonly planetSelected = output<string>();

  protected selectPlanet(entry: PlanetEntry): void {
    if (this.interactive()) this.planetSelected.emit(entry.key);
  }

  protected hitX(anchor: 'start' | 'middle' | 'end'): number {
    if (anchor === 'start') return -4;
    if (anchor === 'end') return -40;
    return -22;
  }

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
        // Center the planet stack vertically on the zone anchor so large
        // stelliums stay inside their (triangular) zone.
        y: point.y - ((planets.length - 1) * 13) / 2 + 4,
        labelX: point.labelX,
        labelY: point.labelY,
        labelAlign: point.labelAlign,
        planetAlign: point.planetAlign,
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
