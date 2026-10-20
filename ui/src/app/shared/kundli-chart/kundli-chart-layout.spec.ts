import { estimateText, fitRegion, FitOptions, FitRegion, Point } from './kundli-chart-layout';

const OPTIONS: FitOptions = { maxSize: 15.5, minSize: 10, floorSize: 8, symbolRatio: 0.82, symbolGap: 3, margin: 3 };

/** North corner triangle (house 12) and diamond (house 1), as the chart draws them. */
const TRIANGLE: Point[] = [[380, 20], [290, 110], [200, 20]];
const DIAMOND: Point[] = [[200, 20], [290, 110], [200, 200], [110, 110]];

const header = [
  { text: 'H12', size: 12.5, kind: 'label' as const },
  { text: 'Cap', size: 14, kind: 'sign' as const },
];

const stellium = ['Su', 'Mo', 'Ma', 'Me', 'Ju', 'Ve', 'Sa', 'Ke'].map((label, i) => ({
  label,
  symbols: i > 1 ? ['↺', '☼'] : [],
}));

function inside(poly: Point[], x: number, y: number): boolean {
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

describe('kundli chart layout', () => {
  it('keeps a quiet house at full size in one column', () => {
    const region: FitRegion = { poly: DIAMOND, anchor: [200, 104], header, entries: [{ label: 'Lagna', symbols: [] }, { label: 'Ma', symbols: ['↑'] }] };
    const fit = fitRegion(region, estimateText, OPTIONS);
    expect(fit.fitted).toBeTrue();
    expect(fit.size).toBe(15.5);
    expect(fit.columns).toBe(1);
  });

  it('fits an eight-planet stellium inside a corner triangle', () => {
    const region: FitRegion = { poly: TRIANGLE, anchor: [290, 54], header, entries: stellium };
    const fit = fitRegion(region, estimateText, OPTIONS);
    expect(fit.fitted).toBeTrue();
    expect(fit.columns).toBeGreaterThan(1);
    expect(fit.size).toBeGreaterThanOrEqual(OPTIONS.floorSize);
    for (const entry of [...fit.entries, ...fit.header]) {
      expect(inside(TRIANGLE, entry.x, entry.y)).withContext(`${entry.x},${entry.y}`).toBeTrue();
    }
  });

  it('keeps planets clear of fixed corner labels', () => {
    const square: Point[] = [[0, 0], [100, 0], [100, 100], [0, 100]];
    const label = { x: 8, y: 8, w: 30, h: 16 };
    const fit = fitRegion({ poly: square, anchor: [50, 48], exclude: [label], entries: stellium }, estimateText, OPTIONS);
    expect(fit.fitted).toBeTrue();
    const rowTop = Math.min(...fit.entries.map((e) => e.y)) - fit.rowHeight / 2;
    const leftmost = Math.min(...fit.entries.filter((e) => e.y - fit.rowHeight / 2 < label.y + label.h).map((e) => e.x), Infinity);
    expect(rowTop >= label.y + label.h || leftmost > label.x + label.w).toBeTrue();
  });

  it('gives back the text zoom of a header before giving up', () => {
    const zoomed = { ...OPTIONS, maxSize: 15.5 * 1.3, minSize: 13 };
    const big = header.map((line) => ({ ...line, size: line.size * 1.3 }));
    const fit = fitRegion({ poly: TRIANGLE, anchor: [290, 54], header: big, entries: stellium }, estimateText, zoomed);
    expect(fit.fitted).toBeTrue();
  });
});
