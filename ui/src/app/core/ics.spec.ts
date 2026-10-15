import { buildIcs } from './ics';

describe('buildIcs', () => {
  const now = new Date('2026-10-15T00:00:00Z');

  it('writes a UTC event with a reminder', () => {
    const ics = buildIcs([{
      uid: 'w1@astrospace',
      title: 'Muhurta: sign a contract',
      startIso: '2026-10-16T10:12:00+05:30',
      endIso: '2026-10-16T11:00:00+05:30',
      location: 'Hyderabad, IN',
      alarmMinutes: 30,
    }], now);
    expect(ics).toContain('DTSTART:20261016T044200Z');
    expect(ics).toContain('DTEND:20261016T053000Z');
    expect(ics).toContain('LOCATION:Hyderabad\\, IN');
    expect(ics).toContain('TRIGGER:-PT30M');
    expect(ics.startsWith('BEGIN:VCALENDAR\r\n')).toBeTrue();
    expect(ics.endsWith('END:VCALENDAR\r\n')).toBeTrue();
  });

  it('writes an all-day event, ending the day after, with a morning alert', () => {
    const ics = buildIcs([{
      uid: 'diwali@astrospace', title: 'Diwali', startIso: '2026-12-31', endIso: '2026-12-31',
      allDay: true, alarmAfterStartMinutes: 420,
    }], now);
    expect(ics).toContain('DTSTART;VALUE=DATE:20261231');
    expect(ics).toContain('DTEND;VALUE=DATE:20270101');
    expect(ics).toContain('TRIGGER:PT420M');
  });

  it('folds long lines at 75 octets', () => {
    const ics = buildIcs([{ uid: 'u', title: 'x'.repeat(200), startIso: '2026-10-16T00:00:00Z', endIso: '2026-10-16T01:00:00Z' }], now);
    for (const line of ics.split('\r\n')) expect(new TextEncoder().encode(line).length).toBeLessThanOrEqual(75);
  });
});
