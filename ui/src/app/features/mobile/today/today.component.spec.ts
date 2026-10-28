import { BAND_LABEL, BAND_OF_TONE, dayScorePosition, muhurtaCountdown } from './today.component';
import { DAY_BANDS } from '../day-gauge/day-gauge.component';

/**
 * Since 2026-10-28 the engine scores the day 0-100 with an ordinary day near
 * 50 (_score_day, astrospace/context/daily.py), and the ring shows that
 * number as it is. Readings cached before then carry the old signed tally and
 * no score_parts; those must still land in their own band's slice.
 */
type Tone = 'supportive' | 'positive' | 'mixed' | 'caution';
const parts = { base: 50, star: 15, moon: -4, transits: 0 };

function bandRange(tone: Tone): [number, number] {
  const [, from, to] = DAY_BANDS.find(([band]) => band === BAND_OF_TONE[tone])!;
  return [from, to];
}

describe('dayScorePosition', () => {
  it('shows the engine score as it is', () => {
    expect(dayScorePosition({ tone: 'positive', score: 61, score_parts: parts } as never)).toBe(61);
    expect(dayScorePosition({ tone: 'supportive', score: 120, score_parts: parts } as never)).toBe(100);
  });

  it('places an old cached tally inside its own band', () => {
    for (const tone of ['supportive', 'positive', 'mixed', 'caution'] as Tone[]) {
      const position = dayScorePosition({ tone, score: -4 } as never);
      const [from, to] = bandRange(tone);
      expect(position).withContext(tone).toBeGreaterThanOrEqual(from);
      expect(position).withContext(tone).toBeLessThan(to);
    }
  });

  it('matches the engine thresholds (70 / 50 / 30)', () => {
    expect(bandRange('supportive')).toEqual([70, 100]);
    expect(bandRange('positive')).toEqual([50, 70]);
    expect(bandRange('mixed')).toEqual([30, 50]);
    expect(bandRange('caution')).toEqual([0, 30]);
  });

  it('uses calm words for every band', () => {
    expect(Object.values(BAND_LABEL)).toEqual(['Good', 'Steady', 'Mixed', 'Go gently']);
  });
});


describe('muhurtaCountdown', () => {
  const daily = {
    date: '2026-10-16',
    provenance: { place: { timezone: 'Asia/Singapore' } },
    muhurta_windows: [{ name: 'Rahu Kalam', time: '11:19–12:50', kind: 'inauspicious' }],
  } as any;
  const at = (hhmm: string) => new Date(`2026-10-16T${hhmm}:00+08:00`);

  it('counts down to the window, then to its end, then says it ended', () => {
    expect(muhurtaCountdown(daily, at('10:49'))).toBe('Starts in 30m');
    expect(muhurtaCountdown(daily, at('12:20'))).toBe('Ends in 30m');
    expect(muhurtaCountdown(daily, at('15:15'))).toBe('Ended');
  });

  it('shows nothing on a cached payload for another day', () => {
    expect(muhurtaCountdown(daily, new Date('2026-10-17T10:00:00+08:00'))).toBe('');
  });
});
