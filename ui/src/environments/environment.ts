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

  // A simulator can reach the host on http://localhost:8000; a physical device
  // cannot and needs the machine's LAN address.
  nativeApiOrigin: '',
};
