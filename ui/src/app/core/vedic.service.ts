import { Injectable, inject } from '@angular/core';

import { ApiService } from './api.service';
import {
  AshtakavargaPayload,
  CalendarIntelligencePayload,
  CompatibilityPayload,
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

  all(kundliId: string): Promise<VedicAll> {
    const cacheKey = `${kundliId}:${this.prefs.ayanamsha()}:${this.prefs.nodeType()}`;
    let cached = this.cache.get(cacheKey);
    if (!cached) {
      cached = this.api.get<VedicAll>(`/vedic/${kundliId}/all?${this.calcParams()}`).catch((e) => {
        this.cache.delete(cacheKey);
        throw e;
      });
      this.cache.set(cacheKey, cached);
    }
    return cached;
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

  ashtakavarga(kundliId: string): Promise<AshtakavargaPayload> {
    return this.api.get<AshtakavargaPayload>(`/vedic/${kundliId}/ashtakavarga?${this.calcParams()}`);
  }

  transitContext(kundliId: string): Promise<TransitContextPayload> {
    return this.api.get<TransitContextPayload>(`/vedic/${kundliId}/transit-context?${this.calcParams()}`);
  }

  transits(kundliId: string): Promise<TransitAnalysisPayload> {
    return this.api.get<TransitAnalysisPayload>(`/vedic/${kundliId}/transits?${this.calcParams()}`);
  }

  gocharam(kundliId: string): Promise<GocharamProfilePayload> {
    return this.api.get<GocharamProfilePayload>(`/vedic/${kundliId}/gocharam?${this.calcParams()}`);
  }

  calendarIntelligence(
    kundliId: string,
    days = 30,
    place?: { city: string; nation: string } | null,
  ): Promise<CalendarIntelligencePayload> {
    const selectedPlace = place ?? this.prefs.panchangaPlace();
    const timezone = this.prefs.effectiveTimezone();
    const params = this.calcParams();
    params.set('days', String(days));
    if (timezone) params.set('timezone', timezone);
    if (selectedPlace?.city) params.set('city', selectedPlace.city);
    if (selectedPlace?.nation) params.set('nation', selectedPlace.nation);
    return this.api.get<CalendarIntelligencePayload>(
      `/vedic/${kundliId}/calendar-intelligence?${params.toString()}`,
    );
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
  }

  invalidateAll(): void {
    this.cache.clear();
  }

  private calcParams(): URLSearchParams {
    return new URLSearchParams({
      ayanamsha: this.prefs.ayanamsha(),
      node_type: this.prefs.nodeType(),
    });
  }
}
