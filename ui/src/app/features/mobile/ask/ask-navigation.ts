import { InjectionToken } from '@angular/core';

/** Shared conversation screens keep their host's route and profile context. */
export interface AskNavigation {
  path: (screen?: string) => string[];
  chart: () => string[];
}

export const ASK_NAVIGATION = new InjectionToken<AskNavigation>('AskNavigation', {
  providedIn: 'root',
  factory: () => ({
    path: (screen) => screen ? ['/m', 'ask', screen] : ['/m', 'ask'],
    chart: () => ['/m', 'chart'],
  }),
});
