import { BAND_LABEL, BAND_OF_TONE, dayBandAt, dayParts, dayScorePosition, muhurtaCountdown, starChangeNote, sunriseNote, widgetMasa, windowSlides } from './today.component';
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

/**
 * A day whose star changes (Hawk, Singapore, 2026-10-30): kind (Sampat) until
 * 11:34, then not (Vipat). The ring shows the part in force now; the sheet
 * lists both; the Timing card counts down to the change.
 */
describe('a day the star changes', () => {
  const SWITCH = '2026-10-30T11:34:39+08:00';
  const verdict = {
    tone: 'positive', score: 2, day_score: 66,
    day_score_periods: [
      { from_iso: '2026-10-30T06:45:56+08:00', until_iso: SWITCH, day_score: 66, tone: 'positive', tara: 'Sampat', tara_favourable: true },
      { from_iso: SWITCH, until_iso: '2026-10-31T06:45:54+08:00', day_score: 43, tone: 'mixed', tara: 'Vipat', tara_favourable: false },
    ],
  };
  const daily = {
    verdict,
    provenance: { place: { timezone: 'Asia/Singapore' } },
    tarabala: { tara: 'Sampat', favourable: true },
    tarabala_periods: [
      { tara: 'Sampat', count: 2, favourable: true, from_iso: '2026-10-30T06:45:56+08:00', until_iso: SWITCH },
      { tara: 'Vipat', count: 3, favourable: false, from_iso: SWITCH, until_iso: '2026-10-31T06:45:54+08:00' },
    ],
  } as never;
  const at = (iso: string) => Date.parse(iso);

  it('draws the ring for the part in force', () => {
    expect(dayScorePosition(verdict as never, at('2026-10-30T10:50:00+08:00'))).toBe(66);
    expect(dayBandAt(verdict as never, at('2026-10-30T10:50:00+08:00'))).toBe('steady');
    expect(dayScorePosition(verdict as never, at('2026-10-30T15:00:00+08:00'))).toBe(43);
    expect(dayBandAt(verdict as never, at('2026-10-30T15:00:00+08:00'))).toBe('mixed');
  });

  it('lists both parts with their times, the current one marked', () => {
    const parts = dayParts(daily, at('2026-10-30T15:00:00+08:00'));
    expect(parts.map((p) => [p.when, p.score, p.label, p.current])).toEqual([
      ['Until 11:34 am', 66, 'Steady', false],
      ['From 11:34 am', 43, 'Mixed', true],
    ]);
  });

  it('counts down to the change, then lets the timing note back', () => {
    const note = starChangeNote(daily, at('2026-10-30T10:50:00+08:00'))!;
    expect(note.value).toBe('Your star turns less kind at 11:34 am. Do the important things before then.');
    expect(note.in).toBe('In 45m');
    expect(starChangeNote(daily, at('2026-10-30T12:00:00+08:00'))).toBeNull();
  });

  it('keeps one ring and no parts on a day of one part', () => {
    const one = { tone: 'positive', score: 2, day_score: 61, day_score_periods: [verdict.day_score_periods[0]] };
    expect(dayScorePosition(one as never, at('2026-10-30T15:00:00+08:00'))).toBe(61);
    expect(dayParts({ ...(daily as object), verdict: one } as never)).toEqual([]);
  });
});

/**
 * Hawk, 2026-10-31, 3:43 am in India: the day of the 31st runs to sunrise on
 * 1 November, and its star changes at 7:12 am on the 31st and again at
 * 5:39 am on the 1st. Today said "Your star turns less kind at 5:39 am" with
 * "In 25h 57m". The 5:39 am change belongs to tomorrow's small hours, and the
 * sunrise sliver until 7:12 is over before most readers are up.
 */
describe('a star change in the small hours after midnight', () => {
  const RISE = '2026-10-31T06:13:51+05:30';
  const MORNING = '2026-10-31T07:12:15+05:30';
  const SMALL_HOURS = '2026-11-01T05:39:54+05:30';
  const NEXT_RISE = '2026-11-01T06:14:14+05:30';
  const verdict = {
    tone: 'positive', score: 2, day_score: 69,
    day_score_periods: [
      { from_iso: RISE, until_iso: MORNING, day_score: 49, tone: 'mixed', tara: 'Janma', tara_favourable: false },
      { from_iso: MORNING, until_iso: SMALL_HOURS, day_score: 69, tone: 'positive', tara: 'Sampat', tara_favourable: true },
      { from_iso: SMALL_HOURS, until_iso: NEXT_RISE, day_score: 60, tone: 'positive', tara: 'Vipat', tara_favourable: false },
    ],
  };
  const daily = {
    verdict,
    provenance: { place: { timezone: 'Asia/Kolkata' } },
    tarabala: { tara: 'Sampat', favourable: true },
    tarabala_periods: [
      { tara: 'Janma', count: 1, favourable: false, from_iso: RISE, until_iso: MORNING },
      { tara: 'Sampat', count: 2, favourable: true, from_iso: MORNING, until_iso: SMALL_HOURS },
      { tara: 'Vipat', count: 3, favourable: false, from_iso: SMALL_HOURS, until_iso: NEXT_RISE },
    ],
  } as never;
  const at = (iso: string) => Date.parse(iso);

  it('does not count down to a change on the next date', () => {
    expect(starChangeNote(daily, at('2026-10-31T03:43:00+05:30'))).toBeNull();
    expect(starChangeNote(daily, at('2026-10-31T20:00:00+05:30'))).toBeNull();
    expect(dayParts(daily, at('2026-10-31T03:43:00+05:30'))).toEqual([]);
  });

  it('draws the ring for the first waking part before it begins', () => {
    expect(dayScorePosition(verdict as never, at('2026-10-31T03:43:00+05:30'))).toBe(69);
    expect(dayScorePosition(verdict as never, at('2026-10-31T06:30:00+05:30'))).toBe(69);
    expect(dayScorePosition(verdict as never, at('2026-10-31T12:00:00+05:30'))).toBe(69);
  });
});

/** Hawk, 2026-10-31: swipe Today's timing note to see the next timings, good and bad. */
describe('windowSlides', () => {
  const daily = {
    date: '2026-10-31',
    provenance: { place: { timezone: 'Asia/Kolkata' } },
    day_windows: [
      { name: 'Brahma Muhurta', kind: 'auspicious', start_iso: '2026-10-31T04:33:59+05:30', end_iso: '2026-10-31T05:23:55+05:30' },
      { name: 'Durmuhurta', kind: 'inauspicious', start_iso: '2026-10-31T06:13:51+05:30', end_iso: '2026-10-31T07:46:02+05:30' },
      { name: 'Rahu Kalam', kind: 'inauspicious', start_iso: '2026-10-31T09:06:43+05:30', end_iso: '2026-10-31T10:33:08+05:30' },
      { name: 'Abhijit Muhurta', kind: 'auspicious', start_iso: '2026-10-31T11:36:31+05:30', end_iso: '2026-10-31T12:22:37+05:30' },
      { name: 'Yamaganda', kind: 'inauspicious', start_iso: '2026-10-31T13:26:00+05:30', end_iso: '2026-10-31T14:52:26+05:30' },
      { name: 'Varjya (Punarvasu)', kind: 'inauspicious', start_iso: '2026-10-31T18:26:05+05:30', end_iso: '2026-10-31T19:55:55+05:30' },
    ],
  } as never;
  const at = (iso: string) => Date.parse(iso);

  it('lists the windows still ahead, good and careful in time order, at most four', () => {
    const slides = windowSlides(daily, at('2026-10-31T08:00:00+05:30'));
    expect(slides.map((s) => [s.title, s.tone])).toEqual([
      ['Rahu Kalam', 'care'], ['Abhijit Muhurta', 'good'], ['Yamaganda', 'care'], ['Varjyam', 'care'],
    ]);
    expect(slides[0].eyebrow).toBe('TAKE CARE');
    expect(slides[0].time).toBe('9:06 am to 10:33 am');
    expect(slides[0].detail).toBe('Good to hold new beginnings till it ends.');
    expect(slides[0].in).toBe('Starts in 1h 7m');
    expect(slides[1].eyebrow).toBe('GOOD TIME');
  });

  it('says when a window runs past midnight', () => {
    const late = { ...(daily as object), date: '2026-10-31', day_windows: [
      { name: 'Bhadra (Vishti Karana)', kind: 'inauspicious', start_iso: '2026-10-31T16:57:50+05:30', end_iso: '2026-11-01T03:52:04+05:30' },
      { name: 'Amrit Kalam (Punarvasu)', kind: 'auspicious', start_iso: '2026-11-01T03:25:08+05:30', end_iso: '2026-11-01T04:54:59+05:30' },
    ] } as never;
    expect(windowSlides(late, at('2026-10-31T12:00:00+05:30')).map((s) => [s.title, s.time])).toEqual([
      ['Bhadra', '4:57 pm to 3:52 am tomorrow'],
      ['Amrit Kalam', '3:25 am to 4:54 am tomorrow'],
    ]);
  });

  it('marks a window that is running and counts down to its end', () => {
    const [first] = windowSlides(daily, at('2026-10-31T09:30:00+05:30'));
    expect(first.title).toBe('Rahu Kalam');
    expect(first.eyebrow).toBe('TAKE CARE · NOW');
    expect(first.in).toBe('Ends in 1h 3m');
  });

  it('shows nothing once the day\'s windows are over, or from a server without them', () => {
    expect(windowSlides(daily, at('2026-10-31T21:00:00+05:30'))).toEqual([]);
    expect(windowSlides({ provenance: { place: { timezone: 'Asia/Kolkata' } } } as never)).toEqual([]);
  });
});
