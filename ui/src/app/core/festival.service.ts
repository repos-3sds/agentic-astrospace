import { Injectable, inject } from '@angular/core';

import { ApiService } from './api.service';
import { FestivalWindowPayload } from './models';
import { FestivalRegion } from './preferences.service';

@Injectable({ providedIn: 'root' })
export class FestivalService {
  private readonly api = inject(ApiService);
  private readonly cache = new Map<string, Promise<FestivalWindowPayload>>();
  private readonly values = new Map<string, FestivalWindowPayload>();
  private readonly storagePrefix = 'astrospace.festivals:v1:';

  upcoming(
    city: string,
    nation: string,
    fromDate: string,
    days: number,
    regions: FestivalRegion[] = [],
  ): Promise<FestivalWindowPayload> {
    const key = this.cacheKey(city, nation, fromDate, days);
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
    city: string,
    nation: string,
    fromDate: string,
    days: number,
    regions: FestivalRegion[] = [],
  ): Promise<FestivalWindowPayload> {
    const key = this.cacheKey(city, nation, fromDate, days);
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
    city: string,
    nation: string,
    fromDate: string,
    days: number,
    regions: FestivalRegion[] = [],
  ): FestivalWindowPayload | null {
    const key = this.cacheKey(city, nation, fromDate, days);
    const memory = this.values.get(key);
    if (memory) return this.filterPayload(memory, regions);
    const stored = this.readStored(key);
    if (stored) this.values.set(key, stored);
    return stored ? this.filterPayload(stored, regions) : null;
  }

  private cacheKey(city: string, nation: string, fromDate: string, days: number): string {
    return new URLSearchParams({
      city,
      nation,
      from_date: fromDate,
      days: String(days),
    }).toString();
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
