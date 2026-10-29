import { BAND_LABEL, BAND_OF_TONE, dayScorePosition, muhurtaCountdown, sunriseNote, widgetMasa } from './today.component';
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
    expect(dayScorePosition({ tone: 'positive', score: 2.4, day_score: 61, day_score_parts: parts } as never)).toBe(61);
    expect(dayScorePosition({ tone: 'supportive', score: 7, day_score: 120, day_score_parts: parts } as never)).toBe(100);
  });

  it('reads a 0-100 score sent before day_score existed', () => {
    expect(dayScorePosition({ tone: 'positive', score: 58, score_parts: parts } as never)).toBe(58);
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

describe('widgetMasa', () => {
  it('names the Amanta rule it uses', () => {
    expect(widgetMasa({ amanta: 'Kartika', purnimanta: 'Margashirsha', adhika: false, paksha: 'Krishna', is_convention_dependent: true, observance_note: '' }))
      .toBe('Kartika (Amanta) · Krishna paksha');
    expect(widgetMasa(null)).toBe('');
  });
});

describe('sunriseNote', () => {
  // Friday 30 Oct 2026 in Singapore, timings from the Indian birth city.
  const daily = {
    date: '2026-10-30',
    valid_from: '2026-10-30T06:12:00+05:30',
    provenance: { place: { timezone: 'Asia/Kolkata' } },
  } as any;

  it('says when the day\'s panchang begins, on the place\'s clock', () => {
    expect(sunriseNote(daily, Date.parse('2026-10-30T05:30:00+08:00'))).toBe('Today\'s panchang begins at sunrise, 6:12 am.');
  });

  it('goes once the sun is up', () => {
    expect(sunriseNote(daily, Date.parse('2026-10-30T06:12:00+05:30'))).toBe('');
    expect(sunriseNote({ ...daily, valid_from: null }, Date.parse('2026-10-30T03:00:00+05:30'))).toBe('');
  });
});
