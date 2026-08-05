import { Injectable, effect, inject, signal } from '@angular/core';

import { ApiService } from './api.service';
import { PanchangaCity } from './models';

export type DefaultChartStyle = 'south' | 'north' | 'eastern';
export type DefaultAyanamsha = 'lahiri' | 'raman' | 'krishnamurti';
export type DefaultNodeType = 'mean' | 'true';
export type TimezoneMode = 'browser' | 'panchanga_place';
export type ExperienceMode = 'guided' | 'balanced' | 'practitioner';
export type ReadingTone = 'gentle' | 'direct';
export type FestivalRegion = 'pan-india' | 'north' | 'south';

export interface PreferencesState {
  chartStyle: DefaultChartStyle;
  ayanamsha: DefaultAyanamsha;
  nodeType: DefaultNodeType;
  timezoneMode: TimezoneMode;
  panchangaPlace: Pick<PanchangaCity, 'city' | 'nation' | 'timezone' | 'label'> | null;
  language: string;
  regionalFormat: string;
  experienceMode: ExperienceMode;
  tone: ReadingTone;
  hapticsEnabled: boolean;
  festivalRegions: FestivalRegion[];
}

interface RemoteSettings {
  exists?: boolean;
  chart_style: DefaultChartStyle;
  ayanamsha: DefaultAyanamsha;
  node_type: DefaultNodeType;
  timezone_mode: TimezoneMode;
  panchanga_place: PreferencesState['panchangaPlace'];
  language: string;
  regional_format: string;
  experience_mode: ExperienceMode;
  tone: ReadingTone;
  updated_at?: string | null;
}

const STORAGE_KEY = 'astrospace-preferences';
const META_STORAGE_KEY = 'astrospace-preferences-meta';
const DEFAULTS: PreferencesState = {
  chartStyle: 'south',
  ayanamsha: 'lahiri',
  nodeType: 'mean',
  timezoneMode: 'browser',
  panchangaPlace: null,
  language: 'en',
  regionalFormat: 'en-IN',
  experienceMode: 'balanced',
  tone: 'gentle',
  hapticsEnabled: true,
  festivalRegions: ['pan-india'],
};

function normalizedFestivalRegions(regions: unknown): FestivalRegion[] {
  const allowed = new Set<FestivalRegion>(['pan-india', 'north', 'south']);
  const raw = Array.isArray(regions) ? regions : [];
  const normalized = [...new Set(raw.filter((region): region is FestivalRegion => allowed.has(region as FestivalRegion)))];
  return normalized.length ? normalized : DEFAULTS.festivalRegions;
}

@Injectable({ providedIn: 'root' })
export class PreferencesService {
  private api = inject(ApiService);

  readonly preferences = signal<PreferencesState>(this.load());

  readonly chartStyle = signal<DefaultChartStyle>(this.preferences().chartStyle);
  readonly ayanamsha = signal<DefaultAyanamsha>(this.preferences().ayanamsha);
  readonly nodeType = signal<DefaultNodeType>(this.preferences().nodeType);
  readonly timezoneMode = signal<TimezoneMode>(this.preferences().timezoneMode);
  readonly panchangaPlace = signal<PreferencesState['panchangaPlace']>(
    this.preferences().panchangaPlace,
  );
  readonly language = signal(this.preferences().language);
  readonly regionalFormat = signal(this.preferences().regionalFormat);
  readonly experienceMode = signal<ExperienceMode>(this.preferences().experienceMode);
  readonly tone = signal<ReadingTone>(this.preferences().tone);
  readonly hapticsEnabled = signal(this.preferences().hapticsEnabled);
  readonly festivalRegions = signal<FestivalRegion[]>(this.preferences().festivalRegions);
  readonly cloudReady = signal(false);
  readonly cloudSaving = signal(false);
  readonly cloudError = signal<string | null>(null);

  private applyingRemote = false;
  private hydrated = false;
  private localUpdatedAt = this.loadMeta().localUpdatedAt;
  private remoteUpdatedAt = this.loadMeta().remoteUpdatedAt;
  private saveTimer: ReturnType<typeof setTimeout> | null = null;
  private syncPromise: Promise<void> | null = null;

  constructor() {
    effect(() => {
      const next: PreferencesState = {
        chartStyle: this.chartStyle(),
        ayanamsha: this.ayanamsha(),
        nodeType: this.nodeType(),
        timezoneMode: this.timezoneMode(),
        panchangaPlace: this.panchangaPlace(),
        language: this.language(),
        regionalFormat: this.regionalFormat(),
        experienceMode: this.experienceMode(),
        tone: this.tone(),
        hapticsEnabled: this.hapticsEnabled(),
        festivalRegions: normalizedFestivalRegions(this.festivalRegions()),
      };
      this.preferences.set(next);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      if (this.hydrated && !this.applyingRemote) {
        this.localUpdatedAt = Date.now();
        this.saveMeta();
      }
      if (this.cloudReady() && !this.applyingRemote) this.queueCloudSave();
      this.hydrated = true;
    });
  }

  setPanchangaPlace(place: PanchangaCity | null): void {
    this.panchangaPlace.set(
      place
        ? {
            city: place.city,
            nation: place.nation,
            timezone: place.timezone,
            label: place.label,
          }
        : null,
    );
  }

  browserTimezone(): string {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  }

  effectiveTimezone(): string {
    if (this.timezoneMode() === 'panchanga_place' && this.panchangaPlace()?.timezone) {
      return this.panchangaPlace()!.timezone;
    }
    return this.browserTimezone();
  }

  reset(): void {
    this.chartStyle.set(DEFAULTS.chartStyle);
    this.ayanamsha.set(DEFAULTS.ayanamsha);
    this.nodeType.set(DEFAULTS.nodeType);
    this.timezoneMode.set(DEFAULTS.timezoneMode);
    this.panchangaPlace.set(DEFAULTS.panchangaPlace);
    this.language.set(DEFAULTS.language);
    this.regionalFormat.set(DEFAULTS.regionalFormat);
    this.experienceMode.set(DEFAULTS.experienceMode);
    this.tone.set(DEFAULTS.tone);
    this.hapticsEnabled.set(DEFAULTS.hapticsEnabled);
    this.festivalRegions.set(DEFAULTS.festivalRegions);
  }

  syncCloud(): Promise<void> {
    if (this.syncPromise) return this.syncPromise;
    this.syncPromise = this.loadCloud().finally(() => {
      this.syncPromise = null;
    });
    return this.syncPromise;
  }

  private load(): PreferencesState {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null') as Partial<PreferencesState> | null;
      const next = { ...DEFAULTS, ...(parsed ?? {}) };
      return { ...next, festivalRegions: normalizedFestivalRegions(next.festivalRegions) };
    } catch {
      return DEFAULTS;
    }
  }

  private async loadCloud(): Promise<void> {
    this.cloudError.set(null);
    try {
      const remote = await this.api.get<RemoteSettings>('/settings');
      if (remote.exists) {
        const remoteTime = remote.updated_at ? Date.parse(remote.updated_at) : 0;
        if (this.localUpdatedAt && remoteTime && this.localUpdatedAt > remoteTime) {
          this.cloudReady.set(true);
          await this.saveCloudNow();
          return;
        }
        this.applyRemote(remote);
        this.remoteUpdatedAt = remoteTime || Date.now();
        this.localUpdatedAt = this.remoteUpdatedAt;
        this.saveMeta();
        this.cloudReady.set(true);
      } else {
        this.cloudReady.set(true);
        await this.saveCloudNow();
      }
    } catch (e) {
      this.cloudError.set((e as Error).message);
    }
  }

  private applyRemote(remote: RemoteSettings): void {
    this.applyingRemote = true;
    try {
      this.chartStyle.set(remote.chart_style);
      this.ayanamsha.set(remote.ayanamsha);
      this.nodeType.set(remote.node_type);
      this.timezoneMode.set(remote.timezone_mode);
      this.panchangaPlace.set(remote.panchanga_place ?? null);
      this.language.set(remote.language || DEFAULTS.language);
      this.regionalFormat.set(remote.regional_format || DEFAULTS.regionalFormat);
      this.experienceMode.set(remote.experience_mode || DEFAULTS.experienceMode);
      this.tone.set(remote.tone || DEFAULTS.tone);
    } finally {
      queueMicrotask(() => {
        this.applyingRemote = false;
      });
    }
  }

  private queueCloudSave(): void {
    if (this.saveTimer) clearTimeout(this.saveTimer);
    this.saveTimer = setTimeout(() => void this.saveCloudNow(), 350);
  }

  private async saveCloudNow(): Promise<void> {
    if (this.applyingRemote) return;
    this.cloudSaving.set(true);
    this.cloudError.set(null);
    try {
      const saved = await this.api.put<RemoteSettings>('/settings', this.toRemote(this.preferences()));
      this.remoteUpdatedAt = saved.updated_at ? Date.parse(saved.updated_at) : Date.now();
      this.localUpdatedAt = this.remoteUpdatedAt;
      this.saveMeta();
    } catch (e) {
      this.cloudError.set((e as Error).message);
    } finally {
      this.cloudSaving.set(false);
    }
  }

  private toRemote(state: PreferencesState): RemoteSettings {
    return {
      chart_style: state.chartStyle,
      ayanamsha: state.ayanamsha,
      node_type: state.nodeType,
      timezone_mode: state.timezoneMode,
      panchanga_place: state.panchangaPlace,
      language: state.language,
      regional_format: state.regionalFormat,
      experience_mode: state.experienceMode,
      tone: state.tone,
    };
  }

  private loadMeta(): { localUpdatedAt: number; remoteUpdatedAt: number } {
    try {
      const parsed = JSON.parse(localStorage.getItem(META_STORAGE_KEY) || 'null') as Partial<{
        localUpdatedAt: number;
        remoteUpdatedAt: number;
      }> | null;
      return {
        localUpdatedAt: typeof parsed?.localUpdatedAt === 'number' ? parsed.localUpdatedAt : 0,
        remoteUpdatedAt: typeof parsed?.remoteUpdatedAt === 'number' ? parsed.remoteUpdatedAt : 0,
      };
    } catch {
      return { localUpdatedAt: 0, remoteUpdatedAt: 0 };
    }
  }

  private saveMeta(): void {
    localStorage.setItem(META_STORAGE_KEY, JSON.stringify({
      localUpdatedAt: this.localUpdatedAt,
      remoteUpdatedAt: this.remoteUpdatedAt,
    }));
  }

}
