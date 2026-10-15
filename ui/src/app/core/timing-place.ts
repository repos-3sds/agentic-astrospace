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

const SOURCE_NOTE: Record<TimingPlaceSource, string> = {
  selected: 'your selected city',
  viewer_timezone: 'nearest listed city to your phone’s timezone',
  birth_city: 'birth city',
};

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
