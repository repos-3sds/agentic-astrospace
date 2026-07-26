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

  // Deliberately the same backend the browser loop verifies against
  // (astrospace-debug, dev-bypass auth). Pointing the simulator at :8000 while
  // verifying screens on :8010 means two different backends prove the same
  // work, which is how "fine in the browser, broken on device" happens.
  //
  // A simulator shares the host's network so localhost reaches it; a physical
  // device does not and needs the machine's LAN address. Cleartext is allowed
  // for local networking only — see the ATS note in ios/App/App/Info.plist.
  nativeApiOrigin: 'http://localhost:8010',
};
