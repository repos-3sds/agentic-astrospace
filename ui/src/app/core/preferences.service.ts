import { Injectable, effect, signal } from '@angular/core';

import { PanchangaCity } from './models';

export type DefaultChartStyle = 'south' | 'north';
export type DefaultAyanamsha = 'lahiri' | 'raman' | 'krishnamurti';
export type DefaultNodeType = 'mean' | 'true';
export type TimezoneMode = 'browser' | 'panchanga_place';

interface PreferencesState {
  chartStyle: DefaultChartStyle;
  ayanamsha: DefaultAyanamsha;
  nodeType: DefaultNodeType;
  timezoneMode: TimezoneMode;
  panchangaPlace: Pick<PanchangaCity, 'city' | 'nation' | 'timezone' | 'label'> | null;
}

const STORAGE_KEY = 'astrospace-preferences';
const DEFAULTS: PreferencesState = {
  chartStyle: 'south',
  ayanamsha: 'lahiri',
  nodeType: 'mean',
  timezoneMode: 'browser',
  panchangaPlace: null,
};

@Injectable({ providedIn: 'root' })
export class PreferencesService {
  readonly preferences = signal<PreferencesState>(this.load());

  readonly chartStyle = signal<DefaultChartStyle>(this.preferences().chartStyle);
  readonly ayanamsha = signal<DefaultAyanamsha>(this.preferences().ayanamsha);
  readonly nodeType = signal<DefaultNodeType>(this.preferences().nodeType);
  readonly timezoneMode = signal<TimezoneMode>(this.preferences().timezoneMode);
  readonly panchangaPlace = signal<PreferencesState['panchangaPlace']>(
    this.preferences().panchangaPlace,
  );

  constructor() {
    effect(() => {
      const next: PreferencesState = {
        chartStyle: this.chartStyle(),
        ayanamsha: this.ayanamsha(),
        nodeType: this.nodeType(),
        timezoneMode: this.timezoneMode(),
        panchangaPlace: this.panchangaPlace(),
      };
      this.preferences.set(next);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
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
  }

  private load(): PreferencesState {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null') as Partial<PreferencesState> | null;
      return { ...DEFAULTS, ...(parsed ?? {}) };
    } catch {
      return DEFAULTS;
    }
  }
}
