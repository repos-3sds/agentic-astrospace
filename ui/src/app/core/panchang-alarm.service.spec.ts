import { TimingsPayload } from './models';
import { DEFAULT_ALARMS, PanchangAlarm, buildNotifications, clock, notificationId } from './panchang-alarm.service';

const win = (name: string, date: string, start: string, end: string) => ({
  name, start, end,
  start_iso: `${date}T${start}:00+05:30`,
  end_iso: `${date}T${end}:00+05:30`,
});

function day(date: string) {
  return {
    date,
    sunrise_iso: `${date}T05:53:00+05:30`,
    sunset_iso: `${date}T17:28:00+05:30`,
    windows: {
      auspicious: [win('Brahma Muhurta', date, '04:15', '05:04'), win('Abhijit Muhurta', date, '11:17', '12:04')],
      inauspicious: [
        win('Rahu Kalam', date, '16:01', '17:28'),
        win('Durmuhurta', date, '15:55', '16:42'),
        win('Durmuhurta (night)', date, '22:10', '22:58'),
      ],
    },
  };
}

const timings: TimingsPayload = {
  place: { city: 'Kakinada', nation: 'IN' } as TimingsPayload['place'],
  days: Array.from({ length: 14 }, (_, i) => day(new Date(Date.UTC(2026, 9, 25 + i)).toISOString().slice(0, 10))),
};

function alarm(id: string, patch: Partial<PanchangAlarm> = {}): PanchangAlarm {
  return { ...DEFAULT_ALARMS.find((a) => a.id === id)!, on: true, ...patch };
}

describe('panchang alarms', () => {
  // 25 Oct 2026, 1 pm in Kakinada.
  const now = new Date('2026-10-25T13:00:00+05:30');
  const oneDay: TimingsPayload = { ...timings, days: [day('2026-10-25'), day('2026-10-26')] };

  it('rings the lead time before the start, in plain words', () => {
    const [first] = buildNotifications(oneDay, [alarm('rahu', { lead: 10 })], now, true);
    expect(first.schedule!.at!.toISOString()).toBe(new Date('2026-10-25T15:51:00+05:30').toISOString());
    expect(first.title).toBe('Rahu Kalam in 10 minutes');
    expect(first.body).toBe('4:01 pm – 5:28 pm. Good to hold new beginnings till it ends.');
    expect(first.channelId).toBe('siddha_windows');
  });

  it('skips a timing that has already passed today and keeps tomorrow\'s', () => {
    const list = buildNotifications(oneDay, [alarm('brahma')], now, true);
    expect(list.filter((n) => n.extra.timing === 'brahma').length).toBe(1);
    expect(list[0].title).toBe('Brahma Muhurta now');
    expect(list[0].channelId).toBe('siddha_alarm');
  });

  it('picks up named variants such as the night Durmuhurta', () => {
    const list = buildNotifications(oneDay, [alarm('durmuhurta', { lead: 0 })], now, true);
    expect(list.map((n) => n.body!.slice(0, 7))).toEqual(['3:55 pm', '10:10 p', '3:55 pm', '10:10 p']);
  });

  it('adds a silent note at the end only when asked', () => {
    const list = buildNotifications(oneDay, [alarm('abhijit', { atEnd: true })], new Date('2026-10-25T09:00:00+05:30'), true);
    const end = list.find((n) => n.title === 'Abhijit Muhurta is over')!;
    expect(end.channelId).toBe('siddha_quiet');
    expect(end.body).toBe('It ended at 12:04 pm.');
  });

  it('names sunrise by its time', () => {
    const [first] = buildNotifications(oneDay, [alarm('sunrise')], now, true);
    expect(first.title).toBe('Sunrise at 5:53 am');
  });

  it('passes the exact-alarm grant through rather than prompting', () => {
    const [first] = buildNotifications(oneDay, [alarm('rahu')], now, false);
    expect(first.isExactNotification).toBeFalse();
  });

  it('asks the reader to open the app on the twelfth day', () => {
    const list = buildNotifications(timings, [alarm('rahu')], now, true);
    const note = list.find((n) => n.title === 'Keep your panchang alarms going')!;
    // 5 Nov is the twelfth day; three hours after its 5:53 am sunrise.
    expect(note.schedule!.at!.toISOString()).toBe(new Date('2026-11-05T08:53:00+05:30').toISOString());
    expect(note.channelId).toBe('siddha_quiet');
  });

  it('never duplicates an id and stays inside its range', () => {
    const all = DEFAULT_ALARMS.map((a) => ({ ...a, on: true, atEnd: true }));
    const list = buildNotifications(timings, all, now, true);
    expect(new Set(list.map((n) => n.id)).size).toBe(list.length);
    expect(list.length).toBeLessThanOrEqual(400);
    expect(notificationId('x')).toBeGreaterThanOrEqual(1_700_000_000);
  });

  it('formats a 24-hour time for the reader', () => {
    expect(clock('00:05')).toBe('12:05 am');
    expect(clock('12:30')).toBe('12:30 pm');
  });

  it('rings at the city clock time on both sides of a clock change', () => {
    // Toronto falls back at 2 am on 1 Nov 2026: the server sends each
    // day's ISO with its own offset, and the phone rings at that instant.
    const toronto: TimingsPayload = {
      place: { city: 'Toronto', nation: 'CA' } as TimingsPayload['place'],
      days: [
        { date: '2026-10-31', sunrise_iso: '2026-10-31T07:51:00-04:00', sunset_iso: '2026-10-31T18:10:00-04:00',
          windows: { auspicious: [], inauspicious: [{ name: 'Rahu Kalam', start: '09:46', end: '11:03',
            start_iso: '2026-10-31T09:46:00-04:00', end_iso: '2026-10-31T11:03:00-04:00' }] } },
        { date: '2026-11-01', sunrise_iso: '2026-11-01T06:52:00-05:00', sunset_iso: '2026-11-01T17:09:00-05:00',
          windows: { auspicious: [], inauspicious: [{ name: 'Rahu Kalam', start: '15:52', end: '17:09',
            start_iso: '2026-11-01T15:52:00-05:00', end_iso: '2026-11-01T17:09:00-05:00' }] } },
      ],
    };
    const list = buildNotifications(toronto, [alarm('rahu', { lead: 0 })], new Date('2026-10-31T00:00:00-04:00'), true);
    expect(list.map((n) => n.schedule!.at!.toISOString())).toEqual([
      '2026-10-31T13:46:00.000Z',
      '2026-11-01T20:52:00.000Z',
    ]);
    expect(list.map((n) => n.body!.slice(0, 7))).toEqual(['9:46 am', '3:52 pm']);
  });
});

