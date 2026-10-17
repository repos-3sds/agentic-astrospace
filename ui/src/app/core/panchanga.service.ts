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

  /**
   * The mobile pickers show 8 rows and searched on every keystroke for 160,
   * which took 5-8 s on a busy server (regression 2026-10-17, R3); they ask
   * for what they show, and a query asked once is answered from memory.
   */
  cities(q = '', limit = 160): Promise<PanchangaCity[]> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (q.trim()) params.set('q', q.trim());
    const key = params.toString();
    const cached = this.cityResults.get(key);
    if (cached) return cached;
    const request = this.api.get<PanchangaCity[]>(`/panchanga/cities?${key}`);
    this.cityResults.set(key, request);
    request.catch(() => this.cityResults.delete(key));
    return request;
  }

  private readonly cityResults = new Map<string, Promise<PanchangaCity[]>>();

  browserTimezone(): string {
    return this.prefs.effectiveTimezone();
  }
}
