import type { AppEnvironment } from './environment.model';

/**
 * Development configuration.
 *
 * Nothing secret belongs here — this file ships to the browser and into the
 * app bundle. Public deployment URLs and the Supabase anon key are fine; the
 * service-role key and any backend secret are not.
 */
export const environment: AppEnvironment = {
  production: false,

  // Web preview still uses the Angular proxy and same-origin `/api` paths.
  // Capacitor is different: the bundle runs from https://localhost inside the
  // phone, so a localhost API origin points at the device itself. Review APKs
  // must therefore use the deployed backend unless a developer intentionally
  // swaps this to a LAN URL for local backend debugging.
  nativeApiOrigin: 'https://agentic-astrospace-cwuqybpnzq-el.a.run.app',
};
