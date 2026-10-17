import { signal } from '@angular/core';

import { festivalPlace } from './festival.service';
import { PreferencesService } from './preferences.service';

describe('festivalPlace', () => {
  function prefs(place: { city: string; nation: string; timezone: string } | null, timezone = 'Asia/Singapore') {
    return { panchangaPlace: signal(place), effectiveTimezone: () => timezone } as unknown as PreferencesService;
  }
  const profile = { birth_city: 'Kothagudem', birth_nation: 'IN' };

  it('uses the city chosen in Settings', () => {
    expect(festivalPlace(prefs({ city: 'London', nation: 'GB', timezone: 'Europe/London' }), profile))
      .toEqual({ city: 'London', nation: 'GB' });
  });

  it('sends the birth city as a fallback with the phone timezone, as the day timings resolve it', () => {
    expect(festivalPlace(prefs(null), profile))
      .toEqual({ city: 'Kothagudem', nation: 'IN', timezone: 'Asia/Singapore', fallback: true });
  });

  it('has nothing to ask for without a city or a profile', () => {
    expect(festivalPlace(prefs(null), null)).toBeNull();
  });
});
