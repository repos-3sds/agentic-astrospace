/**
 * The place a day's windows were computed for, as every timing payload now
 * reports it (`api/timing_place.py`): calendar intelligence, personal
 * panchanga, muhurta search and Today's daily guidance all carry this shape.
 *
 * `source` says which rule chose the place. Windows are always in the
 * place's own clock — a sunrise-relative window has no meaning in another
 * city's time — so the label names the clock rather than letting the reader
 * assume it is the phone's.
 */
export type TimingPlaceSource = 'selected' | 'viewer_timezone' | 'birth_city';

export interface TimingPlacePayload {
  city: string;
  nation?: string;
  timezone?: string;
  source?: TimingPlaceSource;
  viewer_timezone?: string | null;
}

export const SOURCE_NOTE: Record<TimingPlaceSource, string> = {
  selected: 'your selected city',
  viewer_timezone: 'nearest listed city to your phone’s timezone',
  birth_city: 'birth city',
};

/**
 * The place a timing screen will use before the server has answered, said
 * the way the server will decide it (`api/timing_place.py`): the chosen city
 * if there is one, else the listed city nearest the phone's timezone, else
 * the birth city. Settings, Today and Muhurta all describe it with this, so
 * the same rule is never worded three ways.
 */
export function plannedTimingPlace(
  selected: { city: string; nation?: string } | null | undefined,
  viewerTimezone: string,
  at = new Date(),
): { short: string; sentence: string } {
  if (selected?.city) {
    return { short: selected.city, sentence: `${selected.city}, the city you chose` };
  }
  const clock = timezoneShortName(viewerTimezone, at);
  return {
    short: 'Follows phone',
    sentence: `The listed city nearest your phone’s timezone${clock ? ` (${clock})` : ''}, or your birth city`,
  };
}

/** "GMT+5:30" for Asia/Kolkata; falls back to the IANA name. */
export function timezoneShortName(timezone: string | undefined, at = new Date()): string {
  if (!timezone) return '';
  try {
    const part = new Intl.DateTimeFormat('en', { timeZone: timezone, timeZoneName: 'short' })
      .formatToParts(at)
      .find((row) => row.type === 'timeZoneName');
    return part?.value ?? timezone;
  } catch {
    return timezone;
  }
}

/** One line for a card: "Hyderabad · GMT+5:30 (birth city)". */
export function timingPlaceLabel(place: TimingPlacePayload | null | undefined, at = new Date()): string {
  if (!place?.city) return '';
  const clock = timezoneShortName(place.timezone, at);
  const note = place.source ? ` (${SOURCE_NOTE[place.source]})` : '';
  return clock ? `${place.city} · ${clock}${note}` : `${place.city}${note}`;
}

/** The sentence under a list of windows: whose clock the times are in. */
export function timingClockNote(place: TimingPlacePayload | null | undefined, at = new Date()): string {
  if (!place?.city) return '';
  const clock = timezoneShortName(place.timezone, at);
  const differs = !!place.viewer_timezone && !!place.timezone && place.viewer_timezone !== place.timezone;
  if (!differs) return `Times are ${place.city} local time${clock ? ` (${clock})` : ''}.`;
  return `Times are ${place.city} local time${clock ? ` (${clock})` : ''}, not your phone’s (${timezoneShortName(place.viewer_timezone ?? undefined, at)}).`;
}

/**
 * A nudge under Today's place label when the city is a guess. A timezone
 * names a country, not a town (all of India is one zone, and Kolkata's
 * sunrise is an hour before Mumbai's), so a guessed city can put every
 * window tens of minutes off; a chosen city on a phone now in another zone
 * means the reader is likely travelling. Empty when nothing needs saying.
 */
export function timingPlaceHint(place: TimingPlacePayload | null | undefined): string {
  if (!place?.city) return '';
  if (place.source === 'viewer_timezone') {
    return `Times are for ${place.city}, a guess from your phone’s time zone. Set your city for exact times.`;
  }
  if (place.source === 'birth_city') {
    return `Times are for ${place.city}, your birth city. Somewhere else today? Set your city.`;
  }
  if (place.source === 'selected' && place.viewer_timezone && place.timezone
      && place.viewer_timezone !== place.timezone) {
    return `Your phone is on a different clock from ${place.city}. Travelling? Update your city.`;
  }
  return '';
}
