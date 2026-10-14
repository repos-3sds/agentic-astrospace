import { timingClockNote, timingPlaceLabel, timezoneShortName } from './timing-place';

describe('timing place labels', () => {
  const at = new Date('2026-07-07T06:00:00Z');

  it('names the city, its clock and which rule chose it', () => {
    expect(timingPlaceLabel({ city: 'Hyderabad', timezone: 'Asia/Kolkata', source: 'birth_city' }, at))
      .toBe('Hyderabad · GMT+5:30 (birth city)');
    expect(timingPlaceLabel({ city: 'New York', timezone: 'America/New_York', source: 'viewer_timezone' }, at))
      .toBe('New York · EDT (nearest listed city to your phone’s timezone)');
    expect(timingPlaceLabel({ city: 'Chennai', timezone: 'Asia/Kolkata', source: 'selected' }, at))
      .toBe('Chennai · GMT+5:30 (your selected city)');
  });

  it('says plainly when the clock is not the phone’s', () => {
    expect(timingClockNote({ city: 'Hyderabad', timezone: 'Asia/Kolkata', viewer_timezone: 'UTC' }, at))
      .toBe('Times are Hyderabad local time (GMT+5:30), not your phone’s (UTC).');
    expect(timingClockNote({ city: 'Hyderabad', timezone: 'Asia/Kolkata', viewer_timezone: 'Asia/Kolkata' }, at))
      .toBe('Times are Hyderabad local time (GMT+5:30).');
    expect(timingClockNote({ city: 'Hyderabad', timezone: 'Asia/Kolkata' }, at))
      .toBe('Times are Hyderabad local time (GMT+5:30).');
  });

  it('degrades to the IANA name for an unknown zone and to nothing without a place', () => {
    expect(timezoneShortName('Mars/Olympus', at)).toBe('Mars/Olympus');
    expect(timingPlaceLabel(null)).toBe('');
    expect(timingClockNote(undefined)).toBe('');
  });
});
