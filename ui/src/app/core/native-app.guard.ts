import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { Capacitor } from '@capacitor/core';

import { environment } from '../../environments/environment';

/**
 * Keeps the native app screens (`/m/*`) out of the shipped web app.
 *
 * The two front ends share one bundle — see CLAUDE.md — which is what makes a
 * single deploy serve both. It also means that without this guard, anyone who
 * typed `/m` into the browser would land in a half-built native app: five tabs
 * of which three are unrouted, and placeholder readings presented as real ones.
 * That is not a second product, it is a broken first impression of the one we
 * have.
 *
 * Three ways in, in order:
 *
 * - **Native** — the app itself. Always allowed; this is its home.
 * - **Non-production builds** — the browser verification loop the whole screen
 *   build depends on. Every UI bug found so far compiled cleanly and was caught
 *   only by a screenshot at 375x812, so dev keeps the door open deliberately.
 * - **Anything else** — a production web visitor. Sent to the web app's own
 *   home rather than shown a screen that is not finished being built.
 *
 * This is a visibility boundary, not a security one: the mobile code is still
 * in the bundle, and a determined reader can find it. Excluding it outright is
 * a separate build config, which is a bigger change than this problem needs.
 */
export const nativeAppGuard: CanActivateFn = () => {
  if (Capacitor.isNativePlatform() || !environment.production) {
    return true;
  }
  return inject(Router).createUrlTree(['/']);
};
