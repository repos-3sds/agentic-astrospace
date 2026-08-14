import type { ExperienceMode } from '../../../core/preferences.service';

export interface CalendarCacheOptions {
  includePractitionerDetail: boolean;
}

/** Keep month and selected-day requests on the same cache identity. */
export function calendarCacheOptions(mode: ExperienceMode): CalendarCacheOptions {
  return { includePractitionerDetail: mode === 'practitioner' };
}
