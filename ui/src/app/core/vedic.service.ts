import { Injectable, effect, inject } from '@angular/core';

import { ApiService } from './api.service';
import { EntitlementService } from './entitlement.service';
import {
  AshtakavargaPayload,
  BhavaChalitPayload,
  CalendarIntelligencePayload,
  CharaDashaPayload,
  CompatibilityInsightPayload, CompatibilityPayload,
  DailyBriefResponse,
  DailyGuidancePayload,
  DashaPayload,
  GocharamProfilePayload,
  JaiminiPayload,
  Kundli,
  MasaPayload,
  SpecialLagnasPayload,
  TransitAnalysisPayload,
  TransitContextPayload,
  VedicAll,
  VimshopakaBalaPayload,
  YoginiDashaPayload,
  YogasDoshasPayload,
} from './models';
import { ExperienceMode, PreferencesService, ReadingTone } from './preferences.service';
import { TimingPlacePayload } from './timing-place';
import {
  CALENDAR_CACHE_POLICY,
  CHART_CACHE_POLICY,
  CachedResource,
  ResourceCacheIdentity,
  TODAY_CACHE_POLICY,
  resourceCacheKey,
} from './resource-cache';
import { ResourceCacheService } from './resource-cache.service';
import { SessionTeardown } from './session-teardown';

// Must equal the server's constants (astrospace/context/daily.py,
// astrospace/core/vedic/calendar.py); tests/test_client_engine_versions.py
// checks. A mismatch makes every cached read look incompatible and get
// discarded: from #98 until 2026-10-15 the server said 1.1 and this said
// 1.0, so Today never served from cache and an offline launch had nothing.
/** Flags whose answer changes what the chart routes send (`api/vedic_routes.py`, `api/remedy_routes.py`). */
const PLAN_SHAPED = ['vargas.full', 'yogas.full', 'remedies.full'] as const;
const PLAN_SHAPE_KEY = 'astrospace.vedic.plan-shape';

const DAILY_GUIDANCE_ENGINE_VERSION = 'daily-guidance-1.1';
const CALENDAR_ENGINE_VERSION = 'calendar-intelligence-1.0';
const CALENDAR_DATASET_VERSION = 'astrospace-calendar-2026.08.14';

export interface CalendarIntelligenceOptions {
  includePractitionerDetail?: boolean;
  asOf?: string | null;
}

@Injectable({ providedIn: 'root' })
export class VedicService {
  private api = inject(ApiService);
  private prefs = inject(PreferencesService);
  private resourceCache = inject(ResourceCacheService);
  private readonly profileScopes = new Map<string, { userId: string; revision: string }>();
  private cache = new Map<string, Promise<VedicAll>>();
  private allValues = new Map<string, VedicAll>();
  private dailyCache = new Map<string, Promise<DailyGuidancePayload>>();
  private dailyValues = new Map<string, DailyGuidancePayload>();
  private briefCache = new Map<string, Promise<DailyBriefResponse>>();
  private calendarCache = new Map<string, Promise<CalendarIntelligencePayload>>();
  private calendarValues = new Map<string, CalendarIntelligencePayload>();
  private resourceEpoch = 0;
  private detailCache = new Map<string, Promise<unknown>>();
  private detailValues = new Map<string, unknown>();

  constructor() {
    this.resourceCache.discardLegacyUnscopedCaches();
    inject(SessionTeardown).register(() => this.invalidateAll());
    // Once locks are on, the server trims charts and remedy plans to the
    // reader's plan, so a purchase, a lapse or the switch itself must drop
    // what was cached under the old plan, including the copy kept on disk.
    const entitlements = inject(EntitlementService);
    effect(() => {
      const snapshot = entitlements.current();
      if (!snapshot) return;
      const shape = snapshot.quotas_enforced
        ? PLAN_SHAPED.map((key) => (snapshot.entitlements[key] === true ? 1 : 0)).join('')
        : 'open';
      let previous: string | null = null;
      try {
        previous = localStorage.getItem(PLAN_SHAPE_KEY);
        localStorage.setItem(PLAN_SHAPE_KEY, shape);
      } catch {
        // Without storage, only an in-session change is noticed.
      }
      if (previous !== null && previous !== shape) this.invalidateAll();
    });
  }

  configureProfile(profile: Pick<Kundli, 'id' | 'user_id' | 'updated_at'>): void {
    if (!profile.user_id) return;
    const previous = this.profileScopes.get(profile.id);
    const revision = profile.updated_at || 'unversioned';
    if (previous && (previous.userId !== profile.user_id || previous.revision !== revision)) {
      this.resourceEpoch += 1;
    }
    this.profileScopes.set(profile.id, {
      userId: profile.user_id,
      revision,
    });
  }

  removeConfiguredProfile(profileId: string): void {
    this.resourceEpoch += 1;
    this.profileScopes.delete(profileId);
  }

  clearConfiguredProfiles(): void {
    this.resourceEpoch += 1;
    for (const [profileId, scope] of this.profileScopes) {
      this.resourceCache.deleteProfile(scope.userId, profileId);
    }
    this.profileScopes.clear();
    this.dailyCache.clear();
    this.dailyValues.clear();
    this.briefCache.clear();
    clearStoredBriefs();
    this.calendarCache.clear();
    this.calendarValues.clear();
  }

  all(kundliId: string): Promise<VedicAll> {
    const cacheKey = `${kundliId}:${this.prefs.ayanamsha()}:${this.prefs.nodeType()}`;
    let cached = this.cache.get(cacheKey);
    if (!cached) {
      const stored = this.readStoredAll(kundliId);
      if (stored) {
        this.allValues.set(cacheKey, stored);
        cached = Promise.resolve(stored);
        this.cache.set(cacheKey, cached);
      }
    }
    if (!cached) {
      cached = this.api.get<VedicAll>(`/vedic/${kundliId}/all?${this.calcParams()}`).then((value) => {
        this.allValues.set(cacheKey, value);
        this.writeStoredAll(kundliId, value);
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
      this.writeStoredAll(kundliId, value);
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
    const stored = this.readStoredAll(kundliId);
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

  vimshopakaBala(kundliId: string, scheme = 'shodashavarga'): Promise<VimshopakaBalaPayload> {
    const params = this.calcParams();
    params.set('scheme', scheme);
    return this.cachedDetail<VimshopakaBalaPayload>(
      `vimshopaka-bala:${scheme}`,
      kundliId,
      `/vedic/${kundliId}/vimshopaka-bala?${params.toString()}`,
    );
  }

  charaDasha(kundliId: string): Promise<CharaDashaPayload> {
    return this.cachedDetail<CharaDashaPayload>('chara-dasha', kundliId, `/vedic/${kundliId}/chara-dasha?${this.calcParams()}`);
  }

  bhavaChalit(kundliId: string): Promise<BhavaChalitPayload> {
    return this.cachedDetail<BhavaChalitPayload>('bhava-chalit', kundliId, `/vedic/${kundliId}/bhava-chalit?${this.calcParams()}`);
  }

  masa(kundliId: string): Promise<MasaPayload> {
    return this.api.get<MasaPayload>(`/vedic/${kundliId}/masa?${this.calcParams()}`);
  }

  dailyGuidance(kundliId: string): Promise<DailyGuidancePayload> {
    const params = this.dailyParams();
    const identity = this.dailyIdentity(kundliId, params);
    const cacheKey = identity
      ? resourceCacheKey(identity)
      : `volatile:${kundliId}:${this.todayKey()}:${params.toString()}`;
    let cached = this.dailyCache.get(cacheKey);
    if (!cached) {
      const stored = identity
        ? this.resourceCache.get<DailyGuidancePayload>(identity, Date.now(), {
            engineVersion: DAILY_GUIDANCE_ENGINE_VERSION,
          })?.data ?? null
        : null;
      if (stored) {
        this.dailyValues.set(cacheKey, stored);
        cached = Promise.resolve(stored);
        this.dailyCache.set(cacheKey, cached);
      }
    }
    if (!cached) {
      const requestEpoch = this.resourceEpoch;
      cached = this.api.get<DailyGuidancePayload>(`/context/${kundliId}/daily?${params.toString()}`).then((value) => {
        const currentIdentity = this.dailyIdentity(kundliId, this.dailyParams());
        if (this.canCommitResource(requestEpoch, identity, currentIdentity)) {
          this.dailyValues.set(cacheKey, value);
          if (identity) this.cacheDailyGuidance(identity, value);
        }
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
    return this.cachedDailyGuidanceEntry(kundliId)?.data ?? null;
  }

  cachedDailyGuidanceEntry(kundliId: string): CachedResource<DailyGuidancePayload> | null {
    const params = this.dailyParams();
    const identity = this.dailyIdentity(kundliId, params);
    const cacheKey = identity
      ? resourceCacheKey(identity)
      : `volatile:${kundliId}:${this.todayKey()}:${params.toString()}`;
    const memory = this.dailyValues.get(cacheKey);
    if (identity) {
      const stored = this.resourceCache.get<DailyGuidancePayload>(identity, Date.now(), {
        engineVersion: DAILY_GUIDANCE_ENGINE_VERSION,
      });
      if (stored) {
        this.dailyValues.set(cacheKey, stored.data);
        return stored;
      }
      this.dailyValues.delete(cacheKey);
      this.dailyCache.delete(cacheKey);
      return null;
    }
    if (memory) {
      const now = Date.now();
      return {
        data: memory,
        freshness: 'fresh',
        storedAt: now,
        expiresAt: now + TODAY_CACHE_POLICY.expireAfterMs,
      };
    }
    return null;
  }

  /**
   * Today's brief in the agent's words for the Vedic day `date` (the loaded
   * daily payload's date). The server writes it once per day and keeps it;
   * the app keeps it too, in memory and on the device, so reopening Today
   * shows it at once without asking again. A template answer or an error is
   * not kept, so the next open asks again.
   */
  dailyBrief(
    kundliId: string,
    date: string,
    tone: ReadingTone,
    mode: ExperienceMode,
    onFresh?: (value: DailyBriefResponse) => void,
  ): Promise<DailyBriefResponse> {
    const params = this.dailyParams();
    params.set('tone', tone);
    params.set('mode', mode);
    const key = `${BRIEF_STORAGE_PREFIX}${kundliId}:${date}:${params.toString()}`;
    const fetchBrief = () =>
      this.api.get<DailyBriefResponse>(`/context/${kundliId}/daily/brief?${params.toString()}`);
    let cached = this.briefCache.get(key);
    if (!cached) {
      const stored = readStoredBrief(key, date);
      if (stored) {
        cached = Promise.resolve(stored);
        // Shown at once, then checked once per session: the server may hold
        // a newer brief for the day (a new brief format, a rewrite), and a
        // device copy alone would keep the old one until tomorrow.
        void fetchBrief().then((value) => {
          if (!value.brief || value.date !== date) return;
          if (value.generated_at === stored.generated_at && JSON.stringify(value.brief) === JSON.stringify(stored.brief)) return;
          storeBrief(key, value);
          this.briefCache.set(key, Promise.resolve(value));
          onFresh?.(value);
        }).catch(() => undefined);
      } else {
        cached = fetchBrief().then((value) => {
          if (value.brief && value.date === date) storeBrief(key, value);
          else this.briefCache.delete(key);
          return value;
        }).catch((error) => {
          this.briefCache.delete(key);
          throw error;
        });
      }
      this.briefCache.set(key, cached);
    }
    return cached;
  }

  refreshDailyGuidance(kundliId: string): Promise<DailyGuidancePayload> {
    const params = this.dailyParams();
    const identity = this.dailyIdentity(kundliId, params);
    const cacheKey = identity
      ? resourceCacheKey(identity)
      : `volatile:${kundliId}:${this.todayKey()}:${params.toString()}`;
    const requestEpoch = this.resourceEpoch;
    const request = this.api.get<DailyGuidancePayload>(`/context/${kundliId}/daily?${params.toString()}`).then((value) => {
      const currentIdentity = this.dailyIdentity(kundliId, this.dailyParams());
      if (this.canCommitResource(requestEpoch, identity, currentIdentity)) {
        this.dailyValues.set(cacheKey, value);
        if (identity) this.cacheDailyGuidance(identity, value);
      }
      return value;
    }).catch((error) => {
      this.dailyCache.delete(cacheKey);
      throw error;
    });
    this.dailyCache.set(cacheKey, request);
    return request;
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
    options: CalendarIntelligenceOptions = {},
  ): Promise<CalendarIntelligencePayload> {
    const { cacheKey, params, identity } = this.calendarParams(kundliId, days, place, options);
    let cached = this.calendarCache.get(cacheKey);
    if (!cached) {
      const stored = identity
        ? this.resourceCache.get<CalendarIntelligencePayload>(identity, Date.now(), {
            engineVersion: CALENDAR_ENGINE_VERSION,
            datasetVersion: CALENDAR_DATASET_VERSION,
          })?.data ?? null
        : null;
      if (stored) {
        this.calendarValues.set(cacheKey, stored);
        cached = Promise.resolve(stored);
        this.calendarCache.set(cacheKey, cached);
      }
    }
    if (!cached) {
      const requestEpoch = this.resourceEpoch;
      cached = this.api.get<CalendarIntelligencePayload>(
        `/vedic/${kundliId}/calendar-intelligence?${params.toString()}`,
      ).then((value) => {
        const currentIdentity = this.calendarParams(kundliId, days, place, options).identity;
        if (this.canCommitResource(requestEpoch, identity, currentIdentity)) {
          this.calendarValues.set(cacheKey, value);
          if (identity) this.cacheCalendar(identity, value);
        }
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
    options: CalendarIntelligenceOptions = {},
  ): Promise<CalendarIntelligencePayload> {
    const { cacheKey, params, identity } = this.calendarParams(kundliId, days, place, options);
    const requestEpoch = this.resourceEpoch;
    const request = this.api.get<CalendarIntelligencePayload>(
      `/vedic/${kundliId}/calendar-intelligence?${params.toString()}`,
    ).then((value) => {
      const currentIdentity = this.calendarParams(kundliId, days, place, options).identity;
      if (this.canCommitResource(requestEpoch, identity, currentIdentity)) {
        this.calendarValues.set(cacheKey, value);
        if (identity) this.cacheCalendar(identity, value);
      }
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
    options: CalendarIntelligenceOptions = {},
  ): CalendarIntelligencePayload | null {
    return this.cachedCalendarIntelligenceEntry(kundliId, days, place, options)?.data ?? null;
  }

  cachedCalendarIntelligenceEntry(
    kundliId: string,
    days = 30,
    place?: { city: string; nation: string } | null,
    options: CalendarIntelligenceOptions = {},
  ): CachedResource<CalendarIntelligencePayload> | null {
    const { cacheKey, identity } = this.calendarParams(kundliId, days, place, options);
    const memory = this.calendarValues.get(cacheKey);
    if (identity) {
      const stored = this.resourceCache.get<CalendarIntelligencePayload>(identity, Date.now(), {
        engineVersion: CALENDAR_ENGINE_VERSION,
        datasetVersion: CALENDAR_DATASET_VERSION,
      });
      if (stored) {
        this.calendarValues.set(cacheKey, stored.data);
        return stored;
      }
      this.calendarValues.delete(cacheKey);
      this.calendarCache.delete(cacheKey);
      return null;
    }
    if (memory) {
      const now = Date.now();
      return {
        data: memory,
        freshness: 'fresh',
        storedAt: now,
        expiresAt: now + CALENDAR_CACHE_POLICY.expireAfterMs,
      };
    }
    return null;
  }

  compatibility(kundliId: string, partnerId: string): Promise<CompatibilityPayload> {
    return this.api.get<CompatibilityPayload>(
      `/vedic/${kundliId}/compatibility/${partnerId}?${this.calcParams()}`,
    );
  }

  /** The agent-written "About you two" section; `insight` is null when the fixed guidance stays. */
  compatibilityInsight(kundliId: string, partnerId: string, stage: 'married' | 'planning'): Promise<CompatibilityInsightPayload> {
    return this.api.get<CompatibilityInsightPayload>(
      `/vedic/${kundliId}/compatibility/${partnerId}/insight?stage=${stage}&${this.calcParams()}`,
    );
  }

  muhurta(
    kundliId: string,
    goal: string,
    dateFrom: string,
    dateTo: string,
    place?: { city: string; nation: string } | null,
    limit = 5,
    intent?: string | null,
    options: MuhurtaSearchOptions = {},
  ): Promise<MuhurtaSearchPayload> {
    const params = new URLSearchParams({
      goal,
      date_from: dateFrom,
      date_to: dateTo,
      limit: String(limit),
    });
    // A typed purpose ("new car delivery") is scored by the goal it names
    // and checked for refer-out topics on the server.
    if (intent?.trim()) params.set('intent', intent.trim());
    // Same inputs as Calendar Day and Today, so the server resolves the
    // same place for all three (see api/timing_place.py).
    const timezone = this.prefs.effectiveTimezone();
    if (timezone) params.set('timezone', timezone);
    if (place?.city) params.set('city', place.city);
    if (place?.nation) params.set('nation', place.nation);
    if (options.partnerId) params.set('partner_id', options.partnerId);
    if (options.ceremony) params.set('ceremony', options.ceremony);
    if (options.direction) params.set('direction', options.direction);
    if (options.avoid?.length) params.set('avoid', options.avoid.join(','));
    if (options.observeSeason === false) params.set('observe_season', 'false');
    return this.api.get<MuhurtaSearchPayload>(`/muhurta/${kundliId}?${params.toString()}`);
  }

  /** The personal plan: at most three remedies for this profile's running
   * period, its main life area, and one flag only when the chart has one. */
  remedyPlan(kundliId: string): Promise<RemedyPlanPayload> {
    return this.cachedDetail<RemedyPlanPayload>('remedies:plan', kundliId, `/remedies/${kundliId}/plan`);
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
    this.resourceEpoch += 1;
    for (const key of [...this.cache.keys()]) {
      if (key.startsWith(`${kundliId}:`)) this.cache.delete(key);
    }
    for (const key of [...this.allValues.keys()]) {
      if (key.startsWith(`${kundliId}:`)) this.allValues.delete(key);
    }
    // Resource keys are hashed, so profile-scoped invalidation cannot safely
    // infer ownership from the in-memory key. Clear these small request maps.
    this.dailyCache.clear();
    this.dailyValues.clear();
    this.briefCache.clear();
    clearStoredBriefs();
    const scope = this.profileScopes.get(kundliId);
    if (scope) this.resourceCache.deleteProfile(scope.userId, kundliId);
    this.calendarCache.clear();
    this.calendarValues.clear();
    for (const key of [...this.detailCache.keys()]) {
      if (key.startsWith(`${kundliId}:`)) this.detailCache.delete(key);
    }
    for (const key of [...this.detailValues.keys()]) {
      if (key.startsWith(`${kundliId}:`)) this.detailValues.delete(key);
    }
  }

  invalidateAll(): void {
    this.resourceEpoch += 1;
    this.cache.clear();
    this.allValues.clear();
    this.dailyCache.clear();
    this.dailyValues.clear();
    this.briefCache.clear();
    clearStoredBriefs();
    this.calendarCache.clear();
    this.calendarValues.clear();
    this.resourceCache.clearAll();
    this.detailCache.clear();
    this.detailValues.clear();
  }

  private canCommitResource(
    requestEpoch: number,
    requested: ResourceCacheIdentity | null,
    current: ResourceCacheIdentity | null,
  ): boolean {
    if (requestEpoch !== this.resourceEpoch) return false;
    if (!requested) return true;
    return !!current && resourceCacheKey(requested) === resourceCacheKey(current);
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

  /**
   * The chart bundle lives in ResourceCacheService (SQLCipher on native,
   * localStorage on the web) under the owner's identity. Until 2026-10-15 it
   * was written to plaintext localStorage on native too, where anything that
   * can read the WebView's storage could read a person's birth chart, and a
   * sign-out did not remove it. Without an owner (profile not configured yet)
   * it stays in memory only.
   */
  private readStoredAll(kundliId: string): VedicAll | null {
    const identity = this.scopedIdentity(kundliId, 'vedic-all', {});
    if (!identity) return null;
    try {
      return this.resourceCache.get<VedicAll>(identity)?.data ?? null;
    } catch {
      return null;
    }
  }

  private writeStoredAll(kundliId: string, value: VedicAll): void {
    const identity = this.scopedIdentity(kundliId, 'vedic-all', {});
    if (!identity) return;
    try {
      this.resourceCache.set(identity, value, CHART_CACHE_POLICY);
    } catch {
      // The in-memory cache still serves this session.
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
    options: CalendarIntelligenceOptions = {},
  ): { cacheKey: string; params: URLSearchParams; identity: ResourceCacheIdentity | null } {
    const selectedPlace = place ?? this.prefs.panchangaPlace();
    const timezone = this.prefs.effectiveTimezone();
    const params = this.calcParams();
    params.set('days', String(days));
    if (options.asOf) params.set('as_of', options.asOf);
    if (options.includePractitionerDetail) params.set('include_practitioner_detail', 'true');
    if (timezone) params.set('timezone', timezone);
    if (selectedPlace?.city) params.set('city', selectedPlace.city);
    if (selectedPlace?.nation) params.set('nation', selectedPlace.nation);
    const identity = this.scopedIdentity(kundliId, 'calendar', {
      date: options.asOf ?? this.todayKey(),
      timezone,
      city: selectedPlace?.city,
      nation: selectedPlace?.nation,
      variant: `${days}d:${options.includePractitionerDetail ? 'practitioner' : 'standard'}:${options.asOf ?? 'rolling'}`,
    });
    return {
      cacheKey: identity
        ? resourceCacheKey(identity)
        : `volatile:${kundliId}:${this.todayKey()}:${params.toString()}`,
      params,
      identity,
    };
  }

  private dailyIdentity(kundliId: string, params: URLSearchParams): ResourceCacheIdentity | null {
    const place = this.prefs.panchangaPlace();
    return this.scopedIdentity(kundliId, 'today', {
      date: this.todayKey(),
      timezone: this.prefs.effectiveTimezone(),
      city: place?.city,
      nation: place?.nation,
      variant: params.toString(),
    });
  }

  private cacheDailyGuidance(identity: ResourceCacheIdentity, value: DailyGuidancePayload): void {
    this.resourceCache.set(identity, value, TODAY_CACHE_POLICY, Date.now(), 'network', {
      engineVersion: value.engine_version,
      validUntil: value.valid_until,
    });
  }

  private cacheCalendar(identity: ResourceCacheIdentity, value: CalendarIntelligencePayload): void {
    this.resourceCache.set(identity, value, CALENDAR_CACHE_POLICY, Date.now(), 'network', {
      engineVersion: value.engine_version,
      datasetVersion: value.dataset_version,
    });
  }

  private scopedIdentity(
    profileId: string,
    resource: string,
    fields: Partial<ResourceCacheIdentity>,
  ): ResourceCacheIdentity | null {
    const scope = this.profileScopes.get(profileId);
    if (!scope) return null;
    return {
      userId: scope.userId,
      profileId,
      resource,
      schemaVersion: 2,
      profileRevision: scope.revision,
      ayanamsha: this.prefs.ayanamsha(),
      nodeType: this.prefs.nodeType(),
      ...fields,
    };
  }
}

export interface MuhurtaSearchOptions {
  partnerId?: string | null;
  ceremony?: 'day' | 'night' | null;
  direction?: 'north' | 'south' | 'east' | 'west' | null;
  avoid?: string[];
  observeSeason?: boolean;
}

export interface MuhurtaSearchPayload {
  goal: string;
  goal_label: string;
  /** The goal whose rules were used (a typed purpose maps to one). */
  rules_goal?: string;
  rules_label?: string;
  whose?: string;
  date_from: string;
  date_to: string;
  days_scanned: number;
  skipped_days: { date: string; reason: string }[];
  results: MuhurtaApiWindow[];
  count: number;
  /** Slots that cleared the bar but were not returned (raise `limit`). */
  more_available?: number;
  /** The first good slot after the range, when the range was thin. */
  next_good?: { date: string; start: string; end: string; score: number; quality: string; label: string } | null;
  /** What was left out and why, one plain sentence each. */
  notes?: string[];
  note: string | null;
  hours?: number[] | null;
  season_rules?: string[];
  is_convention_dependent: boolean;
  observance_note?: string;
  disclaimer: string;
  capped_to?: string;
  /** Where the windows apply, in whose clock, and which rule chose it. */
  place?: TimingPlacePayload;
}

export interface MuhurtaApiWindow {
  date: string;
  window: string;
  start: string;
  end: string;
  start_iso: string;
  end_iso: string;
  trimmed: boolean;
  /** Any part before 06:00 or after 21:00 at the place. */
  night?: boolean;
  duration_minutes: number;
  score: number;
  quality: 'best' | 'good' | 'workable';
  /** Excellent / Good / Usable. */
  label?: string;
  weekend?: boolean;
  /** Special days: Guru Pushya, Amrit Siddhi, a festival. */
  badges?: string[];
  tithi?: string | null;
  why: { supports: string[]; against: string[]; terms?: string[] };
  vara: string | null;
  nakshatra: string | null;
}

export interface RemedyRecommendationsPayload {
  groups: RemedyRecommendationGroup[];
  count: number;
  note: string | null;
  disclaimer: string;
}

export interface RemedyPlanPayload extends RemedyRecommendationsPayload {
  period: { mahadasha: string | null; antardasha: string | null; start: string | null; end: string | null };
  /** Practices the server left out because the plan shows only the free one. */
  locked_practices?: number;
}

/** One mantra's text in each script the app shows. */
export type MantraVoice = 'male' | 'female';

export interface MantraTake {
  audio_url: string;
  voice_start: number | null;
  voice_seconds: number | null;
}

export interface MantraText {
  te: string;
  en: string;
  sa: string;
  iast: string;
}

export interface RemedyRecommendationGroup {
  recommendation_id: string;
  trigger: {
    kind: string;
    planet?: string;
    dosha?: string;
    level?: string;
    mahadasha?: string;
  };
  /** Plan groups only: why this remedy was picked. */
  slot?: 'period' | 'life_area' | 'flag';
  domain?: string;
  domain_label?: string;
  observance_note?: string | null;
  reason_short: string;
  /** Plan groups only: the reason in plain words, for Guided and Balanced. */
  reason_plain?: string;
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
  /** Plan practices only: the corpus text and its meaning. */
  mantra_id?: string;
  deity?: string | null;
  text?: MantraText;
  meaning?: { en: string | null; te: string | null; hi: string | null };
  kb_citation?: string | null;
  observance_note?: string | null;
  count_note?: string | null;
  fuller_practice?: { mantra_id: string; name: string; note: string | null } | null;
  audio?: {
    text: string;
    transliteration: string;
    language: string;
    count_target: number;
    loop_seconds: number | null;
    audio_url: string | null;
    source_status: string;
    note: string;
    /** Where the voice sits in a recorded track, for the follow-along highlight. */
    voice_start?: number | null;
    voice_seconds?: number | null;
    /** Recorded recitations by voice, when there are any. */
    voices?: Partial<Record<MantraVoice, MantraTake>>;
  };
}

const BRIEF_STORAGE_PREFIX = 'astrospace.brief.';
const BRIEF_STORAGE_LIMIT = 24;

function readStoredBrief(key: string, date: string): DailyBriefResponse | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const value = JSON.parse(raw) as DailyBriefResponse;
    return value?.brief && value.date === date ? value : null;
  } catch {
    return null;
  }
}

/** Keeps the newest briefs only: a day's brief is useless the day after. */
function storeBrief(key: string, value: DailyBriefResponse): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    const keys: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k?.startsWith(BRIEF_STORAGE_PREFIX)) keys.push(k);
    }
    if (keys.length > BRIEF_STORAGE_LIMIT) {
      const dated = keys.map((k) => ({ k, date: k.slice(BRIEF_STORAGE_PREFIX.length).split(':')[1] ?? '' }));
      dated.sort((a, b) => a.date.localeCompare(b.date));
      for (const { k } of dated.slice(0, keys.length - BRIEF_STORAGE_LIMIT)) localStorage.removeItem(k);
    }
  } catch {
    // Storage full or unavailable: the brief still shows, it just isn't kept.
  }
}

function clearStoredBriefs(): void {
  try {
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const k = localStorage.key(i);
      if (k?.startsWith(BRIEF_STORAGE_PREFIX)) localStorage.removeItem(k);
    }
  } catch {
    // Nothing kept, nothing to clear.
  }
}
