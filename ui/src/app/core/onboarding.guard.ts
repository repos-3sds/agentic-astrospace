import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth.service';
import { KundliStore } from './kundli.store';

/** The native app's front door: every cold start is routed through it. */
const ENTRY_PATH = 'm/start';

/**
 * Keeps an onboarded person out of the onboarding screens.
 *
 * System back from the first insight, or a typed `/m/start`, used to land on
 * an empty birth-details form that minted a second "My chart · self" profile
 * on submit. Anyone signed in who already has a self profile is sent to
 * Today instead. Everything else — not signed in, profiles not loadable —
 * lets the screen through: the guard only ever redirects on evidence.
 *
 * One exception, on the entry screen only: a signed-in person whose profiles
 * could not be loaded goes to Today, whose shell says the list failed and
 * offers a retry. Until 2026-10-23 they were shown the welcome screen, which
 * reads exactly like being signed out. Every cold start opens here, and the
 * API's first request after it has scaled to zero takes ~20 s, longer than
 * the read timeout and its retry, so a reader with no cached profile list
 * was "logged out" whenever the app had been idle a while, and signed in
 * again. Supabase's logs showed the session refreshing fine each time.
 */
export const onboardedRedirectGuard: CanActivateFn = async (route) => {
  const auth = inject(AuthService);
  const kundlis = inject(KundliStore);
  const router = inject(Router);
  const entry = route?.routeConfig?.path === ENTRY_PATH;
  const signedInFallback = () =>
    entry && auth.enabled() && !!auth.session() ? router.createUrlTree(['/m', 'today']) : true;
  try {
    await auth.init();
  } catch {
    return signedInFallback();
  }
  if (auth.signedOut() || (auth.enabled() && !auth.isAuthenticated())) return true;
  try {
    await kundlis.load();
  } catch {
    return signedInFallback();
  }
  const hasSelf = kundlis.kundlis().some((k) => (k.relation ?? '').toLowerCase() === 'self');
  return hasSelf ? router.createUrlTree(['/m', 'today']) : true;
};
