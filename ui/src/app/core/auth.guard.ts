import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { Capacitor } from '@capacitor/core';

import { environment } from '../../environments/environment';
import { AdminService } from './admin.service';
import { AuthService } from './auth.service';

/**
 * Signed-in pages of the responsive web app.
 *
 * Since 2026-10-16 Siddha ships to the public only through the store app;
 * asksiddha.app is a landing page (firebase-public/) and the web app is the
 * owner's own tool on the direct Cloud Run address. So a production web
 * visitor also has to be an admin (an active admin_users row, checked by
 * /admin/me). Anyone else signed in is sent to the web landing page.
 *
 * Like nativeAppGuard this is a visibility boundary, not a security one: the
 * API serves every signed-in user their own data whichever client asks, which
 * is what the phone app relies on.
 */
export const authGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const admin = inject(AdminService);
  const router = inject(Router);
  await auth.init();
  if (!auth.isAuthenticated()) return router.createUrlTree(['/auth']);
  if (Capacitor.isNativePlatform() || !environment.production) return true;
  try {
    await admin.me();
    return true;
  } catch {
    return router.createUrlTree(['/']);
  }
};
