import { calendarCacheOptions } from './calendar-cache-options';

describe('calendarCacheOptions', () => {
  it('uses the summary payload for Guided and Balanced calendar routes', () => {
    expect(calendarCacheOptions('guided')).toEqual({ includePractitionerDetail: false });
    expect(calendarCacheOptions('balanced')).toEqual({ includePractitionerDetail: false });
  });

  it('preloads practitioner details before a date is opened', () => {
    expect(calendarCacheOptions('practitioner')).toEqual({ includePractitionerDetail: true });
  });
});
