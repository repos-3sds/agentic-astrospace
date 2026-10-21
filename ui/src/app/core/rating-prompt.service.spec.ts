import { ASK_AGAIN_AFTER_DAYS, MIN_ACTIVE_DAYS, MIN_GOOD_MOMENTS, shouldAsk } from './rating-prompt.service';

describe('rating prompt timing', () => {
  const days = (n: number) => Array.from({ length: n }, (_, i) => `2026-10-${String(i + 1).padStart(2, '0')}`);
  const now = Date.UTC(2026, 9, 21);

  it('waits for enough days and good moments', () => {
    expect(shouldAsk({ days: days(MIN_ACTIVE_DAYS - 1), moments: 10, askedAt: null }, now)).toBeFalse();
    expect(shouldAsk({ days: days(10), moments: MIN_GOOD_MOMENTS - 1, askedAt: null }, now)).toBeFalse();
    expect(shouldAsk({ days: days(MIN_ACTIVE_DAYS), moments: MIN_GOOD_MOMENTS, askedAt: null }, now)).toBeTrue();
  });

  it('asks again only after the quiet period', () => {
    const state = { days: days(10), moments: 10, askedAt: now - (ASK_AGAIN_AFTER_DAYS - 1) * 86_400_000 };
    expect(shouldAsk(state, now)).toBeFalse();
    expect(shouldAsk({ ...state, askedAt: now - ASK_AGAIN_AFTER_DAYS * 86_400_000 }, now)).toBeTrue();
  });
});

import { nativeEventTimes } from './calendar-export';

describe('native calendar times', () => {
  it('turns an all-day festival into UTC midnights with an exclusive end', () => {
    const times = nativeEventTimes({ uid: 'u', title: 'Diwali', startIso: '2026-11-08', endIso: '2026-11-08', allDay: true });
    expect(times.begin).toBe(Date.UTC(2026, 10, 8));
    expect(times.end).toBe(Date.UTC(2026, 10, 9));
  });

  it('keeps a timed window as its instants', () => {
    const times = nativeEventTimes({ uid: 'u', title: 'Abhijit', startIso: '2026-10-21T11:45:00+05:30', endIso: '2026-10-21T12:33:00+05:30' });
    expect(times.begin).toBe(Date.parse('2026-10-21T06:15:00Z'));
    expect(times.end - times.begin).toBe(48 * 60_000);
  });
});
