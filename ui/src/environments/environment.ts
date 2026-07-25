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

  // A simulator shares the host's network, so this reaches a local FastAPI.
  // A physical device does not and needs the machine's LAN address instead.
  // Cleartext is permitted for local networking only — see the ATS note in
  // ios/App/App/Info.plist.
  nativeApiOrigin: 'http://localhost:8000',
};
