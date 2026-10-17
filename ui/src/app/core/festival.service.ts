import { Injectable, inject } from '@angular/core';

import { ApiService } from './api.service';
import { FestivalWindowPayload } from './models';
import { FestivalRegion, PreferencesService } from './preferences.service';

/**
 * Where festival sunrises are taken. Mirrors the day timings' rule
 * (timing_place.resolve_timing_place on the server): the chosen city, else
 * the city for the phone's timezone, else the birth city. The middle step
 * only the server can resolve, so a birth city goes up marked as a fallback
 * with the timezone beside it.
 */
export interface FestivalPlace {
  city: string;
  nation: string;
  timezone?: string;
  fallback?: boolean;
}

export function festivalPlace(
  preferences: PreferencesService,
  profile: { birth_city?: string | null; birth_nation?: string | null } | null | undefined,
): FestivalPlace | null {
  const chosen = preferences.panchangaPlace();
  if (chosen?.city) return { city: chosen.city, nation: chosen.nation || 'IN' };
  if (!profile?.birth_city) return null;
  return {
    city: profile.birth_city,
    nation: profile.birth_nation || 'IN',
    timezone: preferences.effectiveTimezone() || undefined,
    fallback: true,
  };
}

const REGION_LABELS: Record<string, string> = { 'pan-india': 'All India', north: 'North India', south: 'South India' };

/** The festival engine's region ids, as a person would say them. */
export function festivalRegionsLabel(regions: readonly string[]): string {
  return regions.map((region) => REGION_LABELS[region] ?? region).join(' · ');
}

@Injectable({ providedIn: 'root' })
export class FestivalService {
  private readonly api = inject(ApiService);
  private readonly cache = new Map<string, Promise<FestivalWindowPayload>>();
  private readonly values = new Map<string, FestivalWindowPayload>();
  private readonly storagePrefix = 'astrospace.festivals:v1:';

  upcoming(
    place: FestivalPlace,
    fromDate: string,
    days: number,
    regions: FestivalRegion[] = [],
  ): Promise<FestivalWindowPayload> {
    const key = this.cacheKey(place, fromDate, days);
    let cached = this.cache.get(key);
    if (!cached) {
      const stored = this.readStored(key);
      if (stored) {
        this.values.set(key, stored);
        cached = Promise.resolve(stored);
        this.cache.set(key, cached);
      }
    }
    if (!cached) {
      cached = this.api.get<FestivalWindowPayload>(`/festivals/upcoming?${key}`).then((payload) => {
        this.values.set(key, payload);
        this.writeStored(key, payload);
        return payload;
      }).catch((error) => {
        this.cache.delete(key);
        throw error;
      });
      this.cache.set(key, cached);
    }
    return cached.then((payload) => this.filterPayload(payload, regions));
  }

  refreshUpcoming(
    place: FestivalPlace,
    fromDate: string,
    days: number,
    regions: FestivalRegion[] = [],
  ): Promise<FestivalWindowPayload> {
    const key = this.cacheKey(place, fromDate, days);
    const request = this.api.get<FestivalWindowPayload>(`/festivals/upcoming?${key}`).then((payload) => {
      this.values.set(key, payload);
      this.writeStored(key, payload);
      return payload;
    }).catch((error) => {
      this.cache.delete(key);
      throw error;
    });
    this.cache.set(key, request);
    return request.then((payload) => this.filterPayload(payload, regions));
  }

  cachedUpcoming(
    place: FestivalPlace,
    fromDate: string,
    days: number,
    regions: FestivalRegion[] = [],
  ): FestivalWindowPayload | null {
    const key = this.cacheKey(place, fromDate, days);
    const memory = this.values.get(key);
    if (memory) return this.filterPayload(memory, regions);
    const stored = this.readStored(key);
    if (stored) this.values.set(key, stored);
    return stored ? this.filterPayload(stored, regions) : null;
  }

  private cacheKey(place: FestivalPlace, fromDate: string, days: number): string {
    const params = new URLSearchParams({
      city: place.city,
      nation: place.nation,
      from_date: fromDate,
      days: String(days),
    });
    if (place.fallback && place.timezone) {
      params.set('timezone', place.timezone);
      params.set('city_is_fallback', 'true');
    }
    return params.toString();
  }

  private filterPayload(payload: FestivalWindowPayload, regions: FestivalRegion[]): FestivalWindowPayload {
    const selected = [...new Set(regions)];
    if (!selected.length) return payload;
    const keep = new Set(selected);
    const festivals = payload.festivals.filter((festival) =>
      festival.regions.some((region) => keep.has(region as FestivalRegion)),
    );
    return { ...payload, count: festivals.length, festivals };
  }

  private readStored(key: string): FestivalWindowPayload | null {
    try {
      const raw = localStorage.getItem(`${this.storagePrefix}${key}`);
      if (!raw) return null;
      return JSON.parse(raw) as FestivalWindowPayload;
    } catch {
      return null;
    }
  }

  private writeStored(key: string, value: FestivalWindowPayload): void {
    try {
      localStorage.setItem(`${this.storagePrefix}${key}`, JSON.stringify(value));
    } catch {
      // Keep the in-memory cache even if device storage is unavailable.
    }
  }
}
