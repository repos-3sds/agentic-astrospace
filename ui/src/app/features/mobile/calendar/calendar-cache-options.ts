import type { ExperienceMode } from '../../../core/preferences.service';

export interface CalendarCacheOptions {
  includePractitionerDetail: boolean;
}

/** Selected days opt into technical rows only for Practitioner mode. */
export function calendarDayCacheOptions(mode: ExperienceMode): CalendarCacheOptions {
  return { includePractitionerDetail: mode === 'practitioner' };
}
