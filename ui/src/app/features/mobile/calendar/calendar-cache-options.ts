import type { ExperienceMode } from '../../../core/preferences.service';

export interface CalendarCacheOptions {
  includePractitionerDetail: boolean;
}

/** Month grids never need the expensive practitioner payload for every day. */
export function calendarMonthCacheOptions(): CalendarCacheOptions {
  return { includePractitionerDetail: false };
}

/** Selected days opt into technical rows only for Practitioner mode. */
export function calendarDayCacheOptions(mode: ExperienceMode): CalendarCacheOptions {
  return { includePractitionerDetail: mode === 'practitioner' };
}
