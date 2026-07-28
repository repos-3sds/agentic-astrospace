import { gaugePositionFromScore } from './today.component';

/**
 * The day gauge was near-empty for every genuine reading until 2026-07-27:
 * _score_day (astrospace/context/daily.py) returns an unbounded signed
 * tally, and clamping it into 0-100 meant a real -4 day rendered as an
 * empty ring reading 0, while an excellent +5 day rendered as 5 — visually
 * indistinguishable from a bad one. Pure function, no Angular needed.
 */

/**
 * Independent oracle, not read out of gaugePositionFromScore's own band
 * table — mirrors _score_day's thresholds as documented in the function's
 * docstring (supportive >= 3, positive >= 1, mixed >= -1, else caution) and
 * today.component.ts's own gauge-slice comments. If the implementation's
 * bands ever drift from what's documented, this test — not just a read of
 * the source — is what catches it.
 */
type Band = 'supportive' | 'positive' | 'mixed' | 'caution';

function bandFor(score: number): Band {
  if (score >= 3) return 'supportive';
  if (score >= 1) return 'positive';
  if (score >= -1) return 'mixed';
  return 'caution';
}

const GAUGE_RANGE: Record<Band, [number, number]> = {
  supportive: [76, 100],
  positive: [51, 75],
  mixed: [26, 50],
  caution: [1, 25],
};

describe('gaugePositionFromScore', () => {
  it('never contradicts its own band label', () => {
    for (let score = -20; score <= 20; score++) {
      const position = gaugePositionFromScore(score);
      const [floor, ceiling] = GAUGE_RANGE[bandFor(score)];

      expect(position).withContext(`score=${score}`).toBeGreaterThanOrEqual(floor);
      expect(position).withContext(`score=${score}`).toBeLessThanOrEqual(ceiling);
    }
  });

  it('is monotonic: a higher score never shows a lower gauge position', () => {
    let previous = gaugePositionFromScore(-20);
    for (let score = -19; score <= 20; score++) {
      const current = gaugePositionFromScore(score);
      expect(current).withContext(`score=${score} vs previous score`).toBeGreaterThanOrEqual(previous);
      previous = current;
    }
  });

  it('never reaches 0 or clamps like the old 0-100 percentage did', () => {
    // The historical bug, pinned directly: a live reading of -4 used to
    // render as an empty ring (0), and a strong +5 day used to render as
    // literally 5 — both read as "nothing happened" on a 0-100 dial.
    expect(gaugePositionFromScore(-4)).toBeGreaterThan(0);
    expect(gaugePositionFromScore(-4)).not.toBe(0);
    expect(gaugePositionFromScore(5)).toBeGreaterThan(5);
    expect(gaugePositionFromScore(5)).toBe(88); // well into supportive, not saturated yet
    expect(gaugePositionFromScore(7)).toBe(100); // 4 points past the band's start: saturates
  });

  it('stays within the dial for extreme and boundary scores', () => {
    for (const score of [-100, -3, -2, -1, 0, 1, 2, 3, 4, 100]) {
      const position = gaugePositionFromScore(score);
      expect(position).withContext(`score=${score}`).toBeGreaterThanOrEqual(1);
      expect(position).withContext(`score=${score}`).toBeLessThanOrEqual(100);
    }
  });
});
