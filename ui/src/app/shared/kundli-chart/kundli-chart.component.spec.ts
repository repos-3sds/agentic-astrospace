import { TestBed } from '@angular/core/testing';
import { KundliChartComponent } from './kundli-chart.component';
import { VargaChart } from '../../core/models';

const SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'];
const A = 133.33;
const B = 266.67;

/**
 * The classic Bengali/Odia chart, written out independently of the component:
 * Aries fixed in the top middle box and the signs running anticlockwise.
 */
const EASTERN_BOX: Record<string, Array<[number, number]>> = {
  Aries: [[A, 0], [B, 0], [B, A], [A, A]],
  Taurus: [[0, 0], [A, 0], [A, A]],
  Gemini: [[0, 0], [A, A], [0, A]],
  Cancer: [[0, A], [A, A], [A, B], [0, B]],
  Leo: [[0, B], [A, B], [0, 400]],
  Virgo: [[A, B], [A, 400], [0, 400]],
  Libra: [[A, B], [B, B], [B, 400], [A, 400]],
  Scorpio: [[B, B], [400, 400], [B, 400]],
  Sagittarius: [[B, B], [400, B], [400, 400]],
  Capricorn: [[B, A], [400, A], [400, B], [B, B]],
  Aquarius: [[400, 0], [400, A], [B, A]],
  Pisces: [[B, 0], [400, 0], [B, A]],
};

function inside(poly: Array<[number, number]>, x: number, y: number): boolean {
  let sign = 0;
  for (let i = 0; i < poly.length; i++) {
    const [x1, y1] = poly[i];
    const [x2, y2] = poly[(i + 1) % poly.length];
    const cross = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1);
    if (cross === 0) continue;
    if (sign === 0) sign = Math.sign(cross);
    else if (Math.sign(cross) !== sign) return false;
  }
  return true;
}

/** One planet in every sign, so every box is checked. */
function chartWithLagna(lagna: string): VargaChart {
  const planets: VargaChart['planets'] = {};
  SIGNS.forEach((sign, i) => {
    planets[`P${i}`] = { sign, house: ((i - SIGNS.indexOf(lagna) + 12) % 12) + 1 };
  });
  return { name: 'D1', signifies: '', verified_rule: true, lagna: { sign: lagna }, planets };
}

interface Region {
  key: string;
  labels: Array<{ text: string; cls: string; x: number; y: number }>;
  entries: Array<{ entry: { key: string }; x: number; y: number }>;
}

describe('KundliChartComponent eastern chart', () => {
  function regionsFor(lagna: string): Region[] {
    const fixture = TestBed.createComponent(KundliChartComponent);
    fixture.componentRef.setInput('chart', chartWithLagna(lagna));
    fixture.componentRef.setInput('chartStyle', 'eastern');
    fixture.detectChanges();
    return (fixture.componentInstance as unknown as { regions: () => Region[] }).regions();
  }

  for (const lagna of SIGNS) {
    it(`keeps Aries top middle and numbers houses from the Lagna (${lagna} rising)`, () => {
      const regions = regionsFor(lagna);
      expect(regions.length).toBe(12);
      for (const sign of SIGNS) {
        const region = regions.find((r) => r.key === `e${sign}`)!;
        const box = EASTERN_BOX[sign];
        const house = ((SIGNS.indexOf(sign) - SIGNS.indexOf(lagna) + 12) % 12) + 1;
        expect(region.labels.find((l) => l.cls === 'house-number')!.text).toBe(`H${house}`);
        expect(region.labels.find((l) => l.cls === 'sign-label')!.text).toBe(String(SIGNS.indexOf(sign) + 1));
        for (const label of region.labels) {
          expect(inside(box, label.x, label.y)).withContext(`${sign} label ${label.text}`).toBeTrue();
        }
        // The planet in this sign, and the Lagna marker only in the Lagna's sign.
        const keys = region.entries.map((e) => e.entry.key);
        expect(keys).toContain(`P${SIGNS.indexOf(sign)}`);
        expect(keys.includes('Lagna')).toBe(sign === lagna);
        for (const placed of region.entries) {
          expect(inside(box, placed.x, placed.y)).withContext(`${sign} ${placed.entry.key}`).toBeTrue();
        }
      }
    });
  }
});
