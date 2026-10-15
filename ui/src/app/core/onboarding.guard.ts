import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth.service';
import { KundliStore } from './kundli.store';

/**
 * Keeps an onboarded person out of the onboarding screens.
 *
 * System back from the first insight, or a typed `/m/start`, used to land on
 * an empty birth-details form that minted a second "My chart · self" profile
 * on submit. Anyone signed in who already has a self profile is sent to
 * Today instead. Everything else — not signed in, profiles not loadable —
 * lets the screen through: the guard only ever redirects on evidence.
 */
export const onboardedRedirectGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const kundlis = inject(KundliStore);
  const router = inject(Router);
  try {
    await auth.init();
  } catch {
    return true;
  }
  if (auth.signedOut() || (auth.enabled() && !auth.isAuthenticated())) return true;
  try {
    await kundlis.load();
  } catch {
    return true;
  }
  const hasSelf = kundlis.kundlis().some((k) => (k.relation ?? '').toLowerCase() === 'self');
  return hasSelf ? router.createUrlTree(['/m', 'today']) : true;
};
