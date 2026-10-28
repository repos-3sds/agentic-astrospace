import { Injectable, inject } from '@angular/core';

import { ApiService } from './api.service';
import { MonthQualityPayload, PanchangaCity, PanchangaDay, TimingsPayload } from './models';
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

  /** Sunrise, sunset and named windows for the days ahead, for the phone's alarms. */
  timings(kundliId: string, days = 14): Promise<TimingsPayload> {
    const selectedPlace = this.prefs.panchangaPlace();
    const params = new URLSearchParams({ days: String(days), timezone: this.browserTimezone() });
    if (selectedPlace?.city) params.set('city', selectedPlace.city);
    if (selectedPlace?.nation) params.set('nation', selectedPlace.nation);
    return this.api.get<TimingsPayload>(`/panchanga/${kundliId}/timings?${params.toString()}`);
  }

  /** Good / mixed / take-care for each day of a window, for the month grid. */
  month(kundliId: string, fromDate: string, days: number): Promise<MonthQualityPayload> {
    const selectedPlace = this.prefs.panchangaPlace();
    const params = new URLSearchParams({ from_date: fromDate, days: String(days), timezone: this.browserTimezone() });
    if (selectedPlace?.city) params.set('city', selectedPlace.city);
    if (selectedPlace?.nation) params.set('nation', selectedPlace.nation);
    const key = `${kundliId}?${params.toString()}`;
    const cached = this.months.get(key);
    if (cached) return cached;
    const request = this.api.get<MonthQualityPayload>(`/panchanga/${kundliId}/month?${params.toString()}`);
    this.months.set(key, request);
    request.catch(() => this.months.delete(key));
    return request;
  }

  private readonly months = new Map<string, Promise<MonthQualityPayload>>();

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

  /** The nearest place the server knows to an approximate position. */
  nearestCity(lat: number, lng: number): Promise<PanchangaCity> {
    return this.api.post<PanchangaCity>('/panchanga/cities/nearest', { lat, lng });
  }

  browserTimezone(): string {
    return this.prefs.effectiveTimezone();
  }
}
