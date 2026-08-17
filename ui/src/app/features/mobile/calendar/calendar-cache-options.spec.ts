import { calendarDayCacheOptions } from './calendar-cache-options';

describe('calendarCacheOptions', () => {
  it('uses the summary payload for Guided and Balanced selected days', () => {
    expect(calendarDayCacheOptions('guided')).toEqual({ includePractitionerDetail: false });
    expect(calendarDayCacheOptions('balanced')).toEqual({ includePractitionerDetail: false });
  });

  it('requests practitioner details only for the selected day', () => {
    expect(calendarDayCacheOptions('practitioner')).toEqual({ includePractitionerDetail: true });
  });
});
