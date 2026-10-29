import { buildRemedyReminders } from './remedy-reminder.service';
import { crisisSupportFor } from './crisis-support';

describe('buildRemedyReminders', () => {
  const now = new Date(2026, 9, 29, 9, 0); // Thursday 29 Oct, 9 am
  const practice = { title: 'Shani mantra', preferredDay: null, route: '/m/remedies/mantra', updatedAt: now.toISOString() };

  it('reminds daily at 7 am from tomorrow when the practice has no day', () => {
    const out = buildRemedyReminders(practice, now);
    expect(out.length).toBe(14);
    const first = out[0].schedule!.at as Date;
    expect(first.getDate()).toBe(30);
    expect(first.getHours()).toBe(7);
    expect(out[0].extra.route).toBe('/m/remedies/mantra');
  });

  it('reminds weekly on the practice day', () => {
    const out = buildRemedyReminders({ ...practice, preferredDay: 'Saturday' }, now);
    expect(out.length).toBe(6);
    expect(out.every((n) => (n.schedule!.at as Date).getDay() === 6)).toBeTrue();
  });

  it('stops for a practice left alone for a month, or none at all', () => {
    const old = new Date(2026, 8, 1).toISOString();
    expect(buildRemedyReminders({ ...practice, updatedAt: old }, now)).toEqual([]);
    expect(buildRemedyReminders(null, now)).toEqual([]);
  });
});

describe('crisisSupportFor', () => {
  it('gives Tele-MANAS and 112 in India', () => {
    const india = crisisSupportFor('Asia/Kolkata');
    expect(india.lines[0].dial).toBe('14416');
    expect(india.emergency).toBe('112');
  });

  it('tells Canada from the United States', () => {
    expect(crisisSupportFor('America/Toronto').country).toBe('Canada');
    expect(crisisSupportFor('America/Chicago').country).toBe('the United States');
  });

  it('falls back to a directory for a zone it does not know', () => {
    const elsewhere = crisisSupportFor('Africa/Nairobi');
    expect(elsewhere.lines).toEqual([]);
    expect(elsewhere.emergency).toBe('your local emergency number');
  });
});
