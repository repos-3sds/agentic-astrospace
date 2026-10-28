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
 * /admin/me). Anyone else is signed out of the browser again and sent to the
 * sign-in page with `?owner_only=1`, which says the app is where they belong.
 * Until 2026-10-28 they stayed signed in on a landing page whose "Open app"
 * button led straight back here, so it looked dead.
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
  if (await isOwner(admin)) return true;
  await auth.signOut();
  return router.createUrlTree(['/auth'], { queryParams: { owner_only: '1' } });
};

/**
 * The web landing page at '/'. In production it is not shown at all: the
 * public site is asksiddha.app, so a visitor goes there and the owner goes
 * straight into the web app. Development builds keep the page.
 */
export const webLandingGuard: CanActivateFn = async () => {
  if (Capacitor.isNativePlatform() || !environment.production) return true;
  const auth = inject(AuthService);
  const admin = inject(AdminService);
  const router = inject(Router);
  await auth.init();
  if (auth.isAuthenticated() && (await isOwner(admin))) {
    return router.createUrlTree(['/app']);
  }
  if (auth.isAuthenticated()) await auth.signOut();
  leaveForPublicSite();
  return false;
};

async function isOwner(admin: AdminService): Promise<boolean> {
  try {
    await admin.me();
    return true;
  } catch {
    return false;
  }
}

export const PUBLIC_SITE = 'https://asksiddha.app/';

/** A seam for tests: leaving the page cannot be undone inside Karma. */
export const publicSite = { go: (url: string) => window.location.replace(url) };

function leaveForPublicSite(): void {
  publicSite.go(PUBLIC_SITE);
}
