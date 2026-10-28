import { applyMantraTaps, isWidgetRoute, monthDays, wallClockToEpoch, weekDays, windowSpan } from './widget-bridge.service';

describe('widget bridge', () => {
  describe('wallClockToEpoch', () => {
    it('reads a time in the place timezone, not the phone’s', () => {
      expect(wallClockToEpoch('2026-10-17', '14:30', 'Asia/Kolkata')).toBe(Date.UTC(2026, 9, 17, 9, 0));
    });

    it('lands on the right side of a daylight-saving change', () => {
      // New York springs forward at 2 am on 8 March 2026; 3:30 is EDT (UTC-4).
      expect(wallClockToEpoch('2026-03-08', '03:30', 'America/New_York')).toBe(Date.UTC(2026, 2, 8, 7, 30));
      expect(wallClockToEpoch('2026-03-07', '03:30', 'America/New_York')).toBe(Date.UTC(2026, 2, 7, 8, 30));
    });
  });

  describe('windowSpan', () => {
    it('turns a window into start and end times', () => {
      expect(windowSpan('2026-10-17', '10:30–12:00', 'Asia/Kolkata')).toEqual({
        startMs: Date.UTC(2026, 9, 17, 5, 0),
        endMs: Date.UTC(2026, 9, 17, 6, 30),
      });
    });

    it('rolls an end past midnight into the next day', () => {
      const span = windowSpan('2026-10-17', '23:20-00:10', 'Asia/Kolkata')!;
      expect(span.endMs - span.startMs).toBe(50 * 60_000);
    });

    it('skips a window it cannot read', () => {
      expect(windowSpan('2026-10-17', 'all day', 'Asia/Kolkata')).toBeNull();
    });
  });

  describe('weekDays', () => {
    it('gives the calendar widget seven days from today, across a month end', () => {
      const days = weekDays('2026-10-28', [{ date: '2026-10-28', tithi: 'Krishna Tritiya' }], [
        { date: '2026-10-28', quality: 'good' },
        { date: '2026-11-01', quality: 'care' },
      ]);
      expect(days.map((d) => d.date)).toEqual([
        '2026-10-28', '2026-10-29', '2026-10-30', '2026-10-31', '2026-11-01', '2026-11-02', '2026-11-03',
      ]);
      expect(days[0]).toEqual({ date: '2026-10-28', tithi: 'Krishna Tritiya', quality: 'good' });
      expect(days[4].quality).toBe('care');
      // A day the app has nothing for is drawn plain, never guessed.
      expect(days[1]).toEqual({ date: '2026-10-29', tithi: '', quality: '' });
    });
  });

  describe('applyMantraTaps', () => {
    const key = 'siddha.remedyPractice:v1:test:rec:practice';
    afterEach(() => localStorage.removeItem(key));
    const read = () => JSON.parse(localStorage.getItem(key)!);

    it('adds today’s widget taps to today’s count', () => {
      localStorage.setItem(key, JSON.stringify({ count: 10, date: '2026-10-17', target: 108, completedDates: [] }));
      applyMantraTaps(key, 5, '2026-10-17');
      expect(read().count).toBe(15);
    });

    it('starts a new day from zero', () => {
      localStorage.setItem(key, JSON.stringify({ count: 40, date: '2026-10-16', target: 108, completedDates: [] }));
      applyMantraTaps(key, 3, '2026-10-17');
      expect(read()).toEqual(jasmine.objectContaining({ count: 3, date: '2026-10-17' }));
    });

    it('completes the day at the target and stops there', () => {
      localStorage.setItem(key, JSON.stringify({ count: 106, date: '2026-10-17', target: 108, completedDates: ['2026-10-15'] }));
      applyMantraTaps(key, 9, '2026-10-17');
      expect(read().count).toBe(108);
      expect(read().completedDates).toEqual(['2026-10-15', '2026-10-17']);
    });

    it('works for a practice never opened on this phone', () => {
      applyMantraTaps(key, 2, '2026-10-17');
      expect(read().count).toBe(2);
    });
  });
});

describe('isWidgetRoute (D15)', () => {
  it('opens only the widgets’ own screens', () => {
    expect(isWidgetRoute('/m/today')).toBeTrue();
    expect(isWidgetRoute('/m/subhashita')).toBeTrue();
    expect(isWidgetRoute('/m/remedies/mantra?recommendation=r-1&practice=om_namah&profile=abc')).toBeTrue();
    expect(isWidgetRoute('/m/ask/loading?q=when%20will%20I%20die')).toBeFalse();
    expect(isWidgetRoute('/m/settings/account/delete')).toBeFalse();
    expect(isWidgetRoute('/m/remedies/mantra?next=/m/ask')).toBeFalse();
    expect(isWidgetRoute('/m/remedies/mantra?practice=a%20b')).toBeFalse();
    expect(isWidgetRoute('https://evil.example/m/today')).toBeFalse();
  });

  it('lets the iPhone Listen widget open the Listen sheet, and nothing else on Today', () => {
    expect(isWidgetRoute('/m/today?listen=1')).toBeTrue();
    expect(isWidgetRoute('/m/today?listen=1&next=/m/ask')).toBeFalse();
  });
});

describe('monthDays', () => {
  it('lists every day of the month with the qualities that arrived', () => {
    const days = monthDays('2026-02-18', [{ date: '2026-02-01', quality: 'good' }, { date: '2026-03-01', quality: 'care' }]);
    expect(days.length).toBe(28);
    expect(days[0]).toEqual({ date: '2026-02-01', quality: 'good' });
    expect(days[27]).toEqual({ date: '2026-02-28', quality: '' });
  });
});
