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
  private readonly allStoragePrefix = 'astrospace.vedic-all:v1:';
  private dailyCache = new Map<string, Promise<DailyGuidancePayload>>();
  private dailyValues = new Map<string, DailyGuidancePayload>();
  private calendarCache = new Map<string, Promise<CalendarIntelligencePayload>>();
  private calendarValues = new Map<string, CalendarIntelligencePayload>();
  private readonly calendarStoragePrefix = 'astrospace.calendar-intelligence:v1:';
  private detailCache = new Map<string, Promise<unknown>>();
  private detailValues = new Map<string, unknown>();

  all(kundliId: string): Promise<VedicAll> {
    const cacheKey = `${kundliId}:${this.prefs.ayanamsha()}:${this.prefs.nodeType()}`;
    let cached = this.cache.get(cacheKey);
    if (!cached) {
      const stored = this.readStoredAll(cacheKey);
      if (stored) {
        this.allValues.set(cacheKey, stored);
        cached = Promise.resolve(stored);
        this.cache.set(cacheKey, cached);
      }
    }
    if (!cached) {
      cached = this.api.get<VedicAll>(`/vedic/${kundliId}/all?${this.calcParams()}`).then((value) => {
        this.allValues.set(cacheKey, value);
        this.writeStoredAll(cacheKey, value);
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

  refreshAll(kundliId: string): Promise<VedicAll> {
    const cacheKey = `${kundliId}:${this.prefs.ayanamsha()}:${this.prefs.nodeType()}`;
    const request = this.api.get<VedicAll>(`/vedic/${kundliId}/all?${this.calcParams()}`).then((value) => {
      this.allValues.set(cacheKey, value);
      this.writeStoredAll(cacheKey, value);
      return value;
    }).catch((error) => {
      this.cache.delete(cacheKey);
      throw error;
    });
    this.cache.set(cacheKey, request);
    return request;
  }

  cachedAll(kundliId: string): VedicAll | null {
    const cacheKey = `${kundliId}:${this.prefs.ayanamsha()}:${this.prefs.nodeType()}`;
    const memory = this.allValues.get(cacheKey);
    if (memory) return memory;
    const stored = this.readStoredAll(cacheKey);
    if (stored) this.allValues.set(cacheKey, stored);
    return stored;
  }

  dashas(kundliId: string): Promise<DashaPayload> {
    const all = this.cachedAll(kundliId);
    if (all?.dashas) return Promise.resolve(all.dashas);
    return this.cachedDetail<DashaPayload>('dashas', kundliId, `/vedic/${kundliId}/dashas?${this.calcParams()}`);
  }

  yoginiDashas(kundliId: string): Promise<YoginiDashaPayload> {
    return this.cachedDetail<YoginiDashaPayload>('yogini-dashas', kundliId, `/vedic/${kundliId}/yogini-dashas?${this.calcParams()}`);
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
    const all = this.cachedAll(kundliId);
    if (all?.ashtakavarga) return Promise.resolve(all.ashtakavarga);
    return this.cachedDetail<AshtakavargaPayload>('ashtakavarga', kundliId, `/vedic/${kundliId}/ashtakavarga?${this.calcParams()}`);
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
    return this.cachedDetail<GocharamProfilePayload>(
      `gocharam:${scanDays}:${asOf ?? 'today'}`,
      kundliId,
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
      const stored = this.readStoredCalendar(cacheKey);
      if (stored) {
        this.calendarValues.set(cacheKey, stored);
        cached = Promise.resolve(stored);
        this.calendarCache.set(cacheKey, cached);
      }
    }
    if (!cached) {
      cached = this.api.get<CalendarIntelligencePayload>(
        `/vedic/${kundliId}/calendar-intelligence?${params.toString()}`,
      ).then((value) => {
        this.calendarValues.set(cacheKey, value);
        this.writeStoredCalendar(cacheKey, value);
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

  refreshCalendarIntelligence(
    kundliId: string,
    days = 30,
    place?: { city: string; nation: string } | null,
  ): Promise<CalendarIntelligencePayload> {
    const { cacheKey, params } = this.calendarParams(kundliId, days, place);
    const request = this.api.get<CalendarIntelligencePayload>(
      `/vedic/${kundliId}/calendar-intelligence?${params.toString()}`,
    ).then((value) => {
      this.calendarValues.set(cacheKey, value);
      this.writeStoredCalendar(cacheKey, value);
      return value;
    }).catch((error) => {
      this.calendarCache.delete(cacheKey);
      throw error;
    });
    this.calendarCache.set(cacheKey, request);
    return request;
  }

  cachedCalendarIntelligence(
    kundliId: string,
    days = 30,
    place?: { city: string; nation: string } | null,
  ): CalendarIntelligencePayload | null {
    const cacheKey = this.calendarParams(kundliId, days, place).cacheKey;
    const memory = this.calendarValues.get(cacheKey);
    if (memory) return memory;
    const stored = this.readStoredCalendar(cacheKey);
    if (stored) this.calendarValues.set(cacheKey, stored);
    return stored;
  }

  compatibility(kundliId: string, partnerId: string): Promise<CompatibilityPayload> {
    return this.api.get<CompatibilityPayload>(
      `/vedic/${kundliId}/compatibility/${partnerId}?${this.calcParams()}`,
    );
  }

  muhurta(
    kundliId: string,
    goal: string,
    dateFrom: string,
    dateTo: string,
    place?: { city: string; nation: string } | null,
    limit = 5,
  ): Promise<MuhurtaSearchPayload> {
    const params = new URLSearchParams({
      goal,
      date_from: dateFrom,
      date_to: dateTo,
      limit: String(limit),
    });
    if (place?.city) params.set('city', place.city);
    if (place?.nation) params.set('nation', place.nation);
    return this.api.get<MuhurtaSearchPayload>(`/muhurta/${kundliId}?${params.toString()}`);
  }

  remedies(
    kundliId: string,
    options: { includeCostly?: boolean; includeManglik?: boolean; limit?: number } = {},
  ): Promise<RemedyRecommendationsPayload> {
    const params = new URLSearchParams({
      include_costly: String(options.includeCostly ?? false),
      include_manglik: String(options.includeManglik ?? false),
    });
    if (options.limit) params.set('limit', String(options.limit));
    return this.cachedDetail<RemedyRecommendationsPayload>(
      `remedies:${params.toString()}`,
      kundliId,
      `/remedies/${kundliId}?${params.toString()}`,
    );
  }

  yogasDoshas(kundliId: string): Promise<YogasDoshasPayload> {
    const all = this.cachedAll(kundliId);
    if (all?.yogas && all?.doshas) {
      return Promise.resolve({ yogas: all.yogas, doshas: all.doshas });
    }
    return this.cachedDetail<YogasDoshasPayload>('yogas-doshas', kundliId, `/vedic/${kundliId}/yogas-doshas?${this.calcParams()}`);
  }

  invalidate(kundliId: string): void {
    for (const key of [...this.cache.keys()]) {
      if (key.startsWith(`${kundliId}:`)) this.cache.delete(key);
    }
    for (const key of [...this.allValues.keys()]) {
      if (key.startsWith(`${kundliId}:`)) this.allValues.delete(key);
    }
    this.removeStoredAll(`${kundliId}:`);
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
    this.removeStoredCalendars(`${kundliId}:`);
    for (const key of [...this.detailCache.keys()]) {
      if (key.startsWith(`${kundliId}:`)) this.detailCache.delete(key);
    }
    for (const key of [...this.detailValues.keys()]) {
      if (key.startsWith(`${kundliId}:`)) this.detailValues.delete(key);
    }
  }

  invalidateAll(): void {
    this.cache.clear();
    this.allValues.clear();
    this.removeStoredAll();
    this.dailyCache.clear();
    this.dailyValues.clear();
    this.calendarCache.clear();
    this.calendarValues.clear();
    this.removeStoredCalendars();
    this.detailCache.clear();
    this.detailValues.clear();
  }

  private cachedDetail<T>(kind: string, kundliId: string, path: string): Promise<T> {
    const cacheKey = `${kundliId}:${this.prefs.ayanamsha()}:${this.prefs.nodeType()}:${kind}`;
    const value = this.detailValues.get(cacheKey) as T | undefined;
    if (value) return Promise.resolve(value);
    let cached = this.detailCache.get(cacheKey) as Promise<T> | undefined;
    if (!cached) {
      cached = this.api.get<T>(path).then((result) => {
        this.detailValues.set(cacheKey, result);
        return result;
      }).catch((error) => {
        this.detailCache.delete(cacheKey);
        this.detailValues.delete(cacheKey);
        throw error;
      });
      this.detailCache.set(cacheKey, cached);
    }
    return cached;
  }

  private calcParams(): URLSearchParams {
    return new URLSearchParams({
      ayanamsha: this.prefs.ayanamsha(),
      node_type: this.prefs.nodeType(),
    });
  }

  private readStoredAll(cacheKey: string): VedicAll | null {
    try {
      const raw = localStorage.getItem(`${this.allStoragePrefix}${cacheKey}`);
      if (!raw) return null;
      return JSON.parse(raw) as VedicAll;
    } catch {
      return null;
    }
  }

  private writeStoredAll(cacheKey: string, value: VedicAll): void {
    try {
      localStorage.setItem(`${this.allStoragePrefix}${cacheKey}`, JSON.stringify(value));
    } catch {
      // Storage can be full or unavailable; the in-memory cache still serves this session.
    }
  }

  private removeStoredAll(cacheKeyPrefix = ''): void {
    try {
      const prefix = `${this.allStoragePrefix}${cacheKeyPrefix}`;
      for (const key of Object.keys(localStorage)) {
        if (key.startsWith(prefix)) localStorage.removeItem(key);
      }
    } catch {
      // Ignore storage cleanup failures; volatile caches are already cleared.
    }
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
    try {
      return new Intl.DateTimeFormat('en-CA', {
        timeZone: this.prefs.effectiveTimezone(),
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      }).format(new Date());
    } catch {
      return new Date().toISOString().slice(0, 10);
    }
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

  private readStoredCalendar(cacheKey: string): CalendarIntelligencePayload | null {
    try {
      const raw = localStorage.getItem(`${this.calendarStoragePrefix}${cacheKey}`);
      if (!raw) return null;
      return JSON.parse(raw) as CalendarIntelligencePayload;
    } catch {
      return null;
    }
  }

  private writeStoredCalendar(cacheKey: string, value: CalendarIntelligencePayload): void {
    try {
      localStorage.setItem(`${this.calendarStoragePrefix}${cacheKey}`, JSON.stringify(value));
    } catch {
      // Storage can be full or unavailable in private contexts; memory cache still works.
    }
  }

  private removeStoredCalendars(cacheKeyPrefix = ''): void {
    try {
      const prefix = `${this.calendarStoragePrefix}${cacheKeyPrefix}`;
      for (const key of Object.keys(localStorage)) {
        if (key.startsWith(prefix)) localStorage.removeItem(key);
      }
    } catch {
      // Ignore storage cleanup failures; volatile caches are already cleared.
    }
  }
}

export interface MuhurtaSearchPayload {
  goal: string;
  goal_label: string;
  date_from: string;
  date_to: string;
  days_scanned: number;
  skipped_days: { date: string; reason: string }[];
  results: MuhurtaApiWindow[];
  count: number;
  note: string | null;
  is_convention_dependent: boolean;
  disclaimer: string;
}

export interface MuhurtaApiWindow {
  date: string;
  window: string;
  start: string;
  end: string;
  start_iso: string;
  end_iso: string;
  trimmed: boolean;
  duration_minutes: number;
  score: number;
  quality: 'best' | 'good' | 'workable';
  why: { supports: string[]; against: string[] };
  vara: string | null;
  nakshatra: string | null;
}

export interface RemedyRecommendationsPayload {
  groups: RemedyRecommendationGroup[];
  count: number;
  note: string | null;
  disclaimer: string;
}

export interface RemedyRecommendationGroup {
  recommendation_id: string;
  trigger: {
    kind: string;
    planet?: string;
    dosha?: string;
    level?: string;
  };
  reason_short: string;
  reason_practitioner: string;
  evidence: unknown;
  source_status: string;
  tradition_source: string;
  convention_dependent: boolean;
  safety_note: string;
  priority: number;
  practices: RemedyRecommendationPractice[];
}

export interface RemedyRecommendationPractice {
  practice_slug: string;
  type: 'mantra' | 'donation' | 'colour' | 'deity' | 'gem' | string;
  title: string;
  instructions: string;
  cadence: string;
  target_count: number | null;
  preferred_day: string | null;
  optional_cost: boolean;
  planet?: string;
  applies_to?: Record<string, string>;
  tradition_source?: string;
  is_convention_dependent?: boolean;
  audio?: {
    text: string;
    transliteration: string;
    language: string;
    count_target: number;
    loop_seconds: number | null;
    audio_url: string | null;
    source_status: string;
    note: string;
  };
}
