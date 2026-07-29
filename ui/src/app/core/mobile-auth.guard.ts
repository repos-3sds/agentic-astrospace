import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';

/** Protects the native shell while preserving the native sign-in journey. */
export const mobileAuthGuard: CanActivateFn = async () => {
  if (!environment.production) return true;
  const auth = inject(AuthService);
  const router = inject(Router);
  await auth.init();
  return auth.isAuthenticated() ? true : router.createUrlTree(['/m', 'auth']);
};
