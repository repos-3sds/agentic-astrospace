import { Injectable, inject } from '@angular/core';

import { ApiService } from './api.service';
import { FestivalWindowPayload, VratDaysPayload } from './models';
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
  // v2: entries carry the time they were saved. v1 entries were kept forever,
  // so a corrected date (Dussehra 2026, a day late) never reached a phone that
  // had already opened that month.
  private readonly storagePrefix = 'astrospace.festivals:v2:';
  private readonly storedMaxAgeMs = 24 * 60 * 60 * 1000;

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
        // Offline: an older copy beats an error.
        const stale = this.readStored(key, true);
        if (stale) return stale;
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

  /** Ekadashi, Purnima, Amavasya and Pradosham in a window, kept like festivals. */
  vratDays(place: FestivalPlace, fromDate: string, days: number): Promise<VratDaysPayload> {
    const key = this.cacheKey(place, fromDate, days);
    const memory = this.vrats.get(key);
    if (memory) return memory;
    const request = this.api.get<VratDaysPayload>(`/festivals/vrat-days?${key}`);
    this.vrats.set(key, request);
    request.catch(() => this.vrats.delete(key));
    return request;
  }

  private readonly vrats = new Map<string, Promise<VratDaysPayload>>();

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

  /** A stored window, or null when missing or (unless allowStale) over a day old. */
  private readStored(key: string, allowStale = false): FestivalWindowPayload | null {
    try {
      const raw = localStorage.getItem(`${this.storagePrefix}${key}`);
      if (!raw) return null;
      const entry = JSON.parse(raw) as { savedAt?: number; payload?: FestivalWindowPayload };
      if (!entry.payload || typeof entry.savedAt !== 'number') return null;
      if (!allowStale && Date.now() - entry.savedAt > this.storedMaxAgeMs) return null;
      return entry.payload;
    } catch {
      return null;
    }
  }

  private writeStored(key: string, value: FestivalWindowPayload): void {
    try {
      localStorage.setItem(`${this.storagePrefix}${key}`, JSON.stringify({ savedAt: Date.now(), payload: value }));
    } catch {
      // Keep the in-memory cache even if device storage is unavailable.
    }
  }
}
