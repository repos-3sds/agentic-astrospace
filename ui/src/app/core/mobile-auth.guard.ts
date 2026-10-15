import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';

/**
 * Protects the native shell while preserving the native sign-in journey.
 *
 * When auth cannot initialise at all (no network and nothing cached from an
 * earlier launch) the person goes to the sign-in screen rather than a blank
 * shell. AuthService itself handles the common offline case, restoring the
 * cached config and stored session, so this only catches the first-launch
 * and corrupted-cache paths.
 */
export const mobileAuthGuard: CanActivateFn = async () => {
  if (!environment.production) return true;
  const auth = inject(AuthService);
  const router = inject(Router);
  try {
    await auth.init();
  } catch {
    return auth.session() ? true : router.createUrlTree(['/m', 'auth']);
  }
  return auth.isAuthenticated() ? true : router.createUrlTree(['/m', 'auth']);
};
