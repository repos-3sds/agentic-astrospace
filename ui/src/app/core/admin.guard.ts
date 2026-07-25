import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AdminService } from './admin.service';
import { AuthService } from './auth.service';

export const adminGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const admin = inject(AdminService);
  const router = inject(Router);
  await auth.init();
  if (!auth.isAuthenticated()) return router.createUrlTree(['/auth']);
  try {
    await admin.me();
    return true;
  } catch {
    return router.createUrlTree(['/app']);
  }
};
