import { Injectable, inject } from '@angular/core';

import { ApiService } from './api.service';
import { PanchangaCity, PanchangaDay } from './models';
import { PreferencesService } from './preferences.service';

@Injectable({ providedIn: 'root' })
export class PanchangaService {
  private api = inject(ApiService);
  private prefs = inject(PreferencesService);

  today(kundliId: string, place?: Pick<PanchangaCity, 'city' | 'nation'> | null): Promise<PanchangaDay> {
    const selectedPlace = place ?? this.prefs.panchangaPlace();
    const params = new URLSearchParams({ timezone: this.browserTimezone() });
    if (selectedPlace?.city) params.set('city', selectedPlace.city);
    if (selectedPlace?.nation) params.set('nation', selectedPlace.nation);
    return this.api.get<PanchangaDay>(`/panchanga/${kundliId}/today?${params.toString()}`);
  }

  cities(q = ''): Promise<PanchangaCity[]> {
    const params = new URLSearchParams({ limit: '160' });
    if (q.trim()) params.set('q', q.trim());
    return this.api.get<PanchangaCity[]>(`/panchanga/cities?${params.toString()}`);
  }

  browserTimezone(): string {
    return this.prefs.effectiveTimezone();
  }
}
