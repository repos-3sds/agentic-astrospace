import { Injectable, inject } from '@angular/core';

import { ApiService } from './api.service';
import {
  AshtakavargaPayload,
  CalendarIntelligencePayload,
  CompatibilityPayload,
  DailyGuidancePayload,
  DashaPayload,
  GocharamProfilePayload,
  JaiminiPayload,
  MasaPayload,
  SpecialLagnasPayload,
  TransitAnalysisPayload,
  TransitContextPayload,
  VedicAll,
  YoginiDashaPayload,
  YogasDoshasPayload,
} from './models';
import { PreferencesService } from './preferences.service';

@Injectable({ providedIn: 'root' })
export class VedicService {
  private api = inject(ApiService);
  private prefs = inject(PreferencesService);
  private cache = new Map<string, Promise<VedicAll>>();
  private allValues = new Map<string, VedicAll>();
  private dailyCache = new Map<string, Promise<DailyGuidancePayload>>();
  private dailyValues = new Map<string, DailyGuidancePayload>();
  private calendarCache = new Map<string, Promise<CalendarIntelligencePayload>>();
  private calendarValues = new Map<string, CalendarIntelligencePayload>();

  all(kundliId: string): Promise<VedicAll> {
    const cacheKey = `${kundliId}:${this.prefs.ayanamsha()}:${this.prefs.nodeType()}`;
    let cached = this.cache.get(cacheKey);
    if (!cached) {
      cached = this.api.get<VedicAll>(`/vedic/${kundliId}/all?${this.calcParams()}`).then((value) => {
        this.allValues.set(cacheKey, value);
        return value;
      }).catch((e) => {
        this.cache.delete(cacheKey);
        this.allValues.delete(cacheKey);
        throw e;
      });
      this.cache.set(cacheKey, cached);
    }
    return cached;
  }

  cachedAll(kundliId: string): VedicAll | null {
    return this.allValues.get(`${kundliId}:${this.prefs.ayanamsha()}:${this.prefs.nodeType()}`) ?? null;
  }

  dashas(kundliId: string): Promise<DashaPayload> {
    return this.api.get<DashaPayload>(`/vedic/${kundliId}/dashas?${this.calcParams()}`);
  }

  yoginiDashas(kundliId: string): Promise<YoginiDashaPayload> {
    return this.api.get<YoginiDashaPayload>(`/vedic/${kundliId}/yogini-dashas?${this.calcParams()}`);
  }

  jaimini(kundliId: string): Promise<JaiminiPayload> {
    return this.api.get<JaiminiPayload>(`/vedic/${kundliId}/jaimini?${this.calcParams()}`);
  }

  specialLagnas(kundliId: string): Promise<SpecialLagnasPayload> {
    return this.api.get<SpecialLagnasPayload>(`/vedic/${kundliId}/special-lagnas?${this.calcParams()}`);
  }

  masa(kundliId: string): Promise<MasaPayload> {
    return this.api.get<MasaPayload>(`/vedic/${kundliId}/masa?${this.calcParams()}`);
  }

  dailyGuidance(kundliId: string): Promise<DailyGuidancePayload> {
    const params = this.dailyParams();
    const cacheKey = `${kundliId}:${this.todayKey()}:${params.toString()}`;
    let cached = this.dailyCache.get(cacheKey);
    if (!cached) {
      cached = this.api.get<DailyGuidancePayload>(`/context/${kundliId}/daily?${params.toString()}`).then((value) => {
        this.dailyValues.set(cacheKey, value);
        return value;
      }).catch((e) => {
        this.dailyCache.delete(cacheKey);
        this.dailyValues.delete(cacheKey);
        throw e;
      });
      this.dailyCache.set(cacheKey, cached);
    }
    return cached;
  }

  cachedDailyGuidance(kundliId: string): DailyGuidancePayload | null {
    return this.dailyValues.get(`${kundliId}:${this.todayKey()}:${this.dailyParams().toString()}`) ?? null;
  }

  ashtakavarga(kundliId: string): Promise<AshtakavargaPayload> {
    return this.api.get<AshtakavargaPayload>(`/vedic/${kundliId}/ashtakavarga?${this.calcParams()}`);
  }

  transitContext(kundliId: string): Promise<TransitContextPayload> {
    return this.api.get<TransitContextPayload>(`/vedic/${kundliId}/transit-context?${this.calcParams()}`);
  }

  transits(kundliId: string): Promise<TransitAnalysisPayload> {
    return this.api.get<TransitAnalysisPayload>(`/vedic/${kundliId}/transits?${this.calcParams()}`);
  }

  gocharam(
    kundliId: string,
    scanDays = 90,
    asOf?: string | null,
  ): Promise<GocharamProfilePayload> {
    const params = this.calcParams();
    params.set('scan_days', String(scanDays));
    if (asOf) params.set('as_of', asOf);
    return this.api.get<GocharamProfilePayload>(
      `/vedic/${kundliId}/gocharam?${params.toString()}`,
    );
  }

  calendarIntelligence(
    kundliId: string,
    days = 30,
    place?: { city: string; nation: string } | null,
  ): Promise<CalendarIntelligencePayload> {
    const { cacheKey, params } = this.calendarParams(kundliId, days, place);
    let cached = this.calendarCache.get(cacheKey);
    if (!cached) {
      cached = this.api.get<CalendarIntelligencePayload>(
        `/vedic/${kundliId}/calendar-intelligence?${params.toString()}`,
      ).then((value) => {
        this.calendarValues.set(cacheKey, value);
        return value;
      }).catch((e) => {
        this.calendarCache.delete(cacheKey);
        this.calendarValues.delete(cacheKey);
        throw e;
      });
      this.calendarCache.set(cacheKey, cached);
    }
    return cached;
  }

  cachedCalendarIntelligence(
    kundliId: string,
    days = 30,
    place?: { city: string; nation: string } | null,
  ): CalendarIntelligencePayload | null {
    return this.calendarValues.get(this.calendarParams(kundliId, days, place).cacheKey) ?? null;
  }

  compatibility(kundliId: string, partnerId: string): Promise<CompatibilityPayload> {
    return this.api.get<CompatibilityPayload>(
      `/vedic/${kundliId}/compatibility/${partnerId}?${this.calcParams()}`,
    );
  }

  yogasDoshas(kundliId: string): Promise<YogasDoshasPayload> {
    return this.api.get<YogasDoshasPayload>(`/vedic/${kundliId}/yogas-doshas?${this.calcParams()}`);
  }

  invalidate(kundliId: string): void {
    for (const key of [...this.cache.keys()]) {
      if (key.startsWith(`${kundliId}:`)) this.cache.delete(key);
    }
    for (const key of [...this.allValues.keys()]) {
      if (key.startsWith(`${kundliId}:`)) this.allValues.delete(key);
    }
    for (const key of [...this.dailyCache.keys()]) {
      if (key.startsWith(`${kundliId}:`)) this.dailyCache.delete(key);
    }
    for (const key of [...this.dailyValues.keys()]) {
      if (key.startsWith(`${kundliId}:`)) this.dailyValues.delete(key);
    }
    for (const key of [...this.calendarCache.keys()]) {
      if (key.startsWith(`${kundliId}:`)) this.calendarCache.delete(key);
    }
    for (const key of [...this.calendarValues.keys()]) {
      if (key.startsWith(`${kundliId}:`)) this.calendarValues.delete(key);
    }
  }

  invalidateAll(): void {
    this.cache.clear();
    this.allValues.clear();
    this.dailyCache.clear();
    this.dailyValues.clear();
    this.calendarCache.clear();
    this.calendarValues.clear();
  }

  private calcParams(): URLSearchParams {
    return new URLSearchParams({
      ayanamsha: this.prefs.ayanamsha(),
      node_type: this.prefs.nodeType(),
    });
  }

  private dailyParams(): URLSearchParams {
    const params = this.calcParams();
    const timezone = this.prefs.effectiveTimezone();
    const place = this.prefs.panchangaPlace();
    if (timezone) params.set('timezone', timezone);
    if (place?.city) params.set('city', place.city);
    if (place?.nation) params.set('nation', place.nation);
    return params;
  }

  private todayKey(): string {
    return new Date().toISOString().slice(0, 10);
  }

  private calendarParams(
    kundliId: string,
    days: number,
    place?: { city: string; nation: string } | null,
  ): { cacheKey: string; params: URLSearchParams } {
    const selectedPlace = place ?? this.prefs.panchangaPlace();
    const timezone = this.prefs.effectiveTimezone();
    const params = this.calcParams();
    params.set('days', String(days));
    if (timezone) params.set('timezone', timezone);
    if (selectedPlace?.city) params.set('city', selectedPlace.city);
    if (selectedPlace?.nation) params.set('nation', selectedPlace.nation);
    return { cacheKey: `${kundliId}:${this.todayKey()}:${params.toString()}`, params };
  }
}
