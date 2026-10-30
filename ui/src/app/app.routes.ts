import { inject } from '@angular/core';
import { CanMatchFn, Router, Routes } from '@angular/router';
import { Capacitor } from '@capacitor/core';
import { nativeAppGuard } from './core/native-app.guard';
import { onboardedRedirectGuard, promiseSeenGuard } from './core/onboarding.guard';
import { mobileAuthGuard } from './core/mobile-auth.guard';
import { MOBILE_ROUTES } from './features/mobile/mobile.routes';

/** '/' inside the native app is its entry screen; on the web it falls through to the landing page. */
const nativeRootRedirect: CanMatchFn = () =>
  Capacitor.isNativePlatform() ? inject(Router).parseUrl('/m/start') : false;

export const routes: Routes = [
  // The native app opens on its own entry screen. Matched before the web
  // shell so a native launch never loads the web chunk (PrimeNG and all) just
  // to be redirected away from '/'.
  {
    path: '',
    pathMatch: 'full',
    canMatch: [nativeRootRedirect],
    children: [],
  },
  // Native app screens (Figma RRhuTcaKIhqILZW7JUKFzI). Namespaced under /m so
  // the existing web routes are untouched and both can ship from one bundle.
  // Onboarding sits outside the shell — no tab bar until there is an app to
  // navigate. These must precede the 'm' route below: that route's child '**'
  // would otherwise swallow every path under /m and redirect it to today.
  {
    path: 'm/start',
    canActivate: [nativeAppGuard, onboardedRedirectGuard],
    loadComponent: () =>
      import('./features/mobile/onboarding/landing.component').then((m) => m.LandingComponent),
  },
  {
    path: 'm/auth',
    canActivate: [nativeAppGuard],
    loadComponent: () =>
      import('./features/mobile/onboarding/mobile-auth.component').then(
        (m) => m.MobileAuthComponent,
      ),
  },
  {
    path: 'm/forgot-password',
    canActivate: [nativeAppGuard],
    loadComponent: () =>
      import('./features/mobile/onboarding/forgot-password.component').then(
        (m) => m.ForgotPasswordComponent,
      ),
  },
  {
    path: 'm/reset-password',
    canActivate: [nativeAppGuard],
    loadComponent: () =>
      import('./features/mobile/onboarding/reset-password.component').then(
        (m) => m.ResetPasswordComponent,
      ),
  },
  {
    path: 'm/language',
    canActivate: [nativeAppGuard, onboardedRedirectGuard],
    loadComponent: () =>
      import('./features/mobile/onboarding/language.component').then((m) => m.LanguageComponent),
  },
  {
    path: 'm/disclaimers',
    canActivate: [nativeAppGuard, onboardedRedirectGuard],
    loadComponent: () =>
      import('./features/mobile/onboarding/disclaimers.component').then(
        (m) => m.DisclaimersComponent,
      ),
  },
  {
    // Persona and chart style come after birth details, so the profile
    // already exists here; the onboarded redirect would skip them.
    path: 'm/persona',
    canActivate: [nativeAppGuard, mobileAuthGuard],
    loadComponent: () =>
      import('./features/mobile/onboarding/persona.component').then((m) => m.PersonaComponent),
  },
  {
    path: 'm/customize',
    canActivate: [nativeAppGuard, mobileAuthGuard],
    loadComponent: () =>
      import('./features/mobile/onboarding/customize.component').then(
        (m) => m.CustomizeComponent,
      ),
  },
  {
    path: 'm/birth-details',
    canActivate: [nativeAppGuard, onboardedRedirectGuard, promiseSeenGuard],
    loadComponent: () =>
      import('./features/mobile/onboarding/birth-details.component').then(
        (m) => m.BirthDetailsComponent,
      ),
  },
  {
    path: 'm/insight',
    canActivate: [nativeAppGuard],
    loadComponent: () =>
      import('./features/mobile/onboarding/first-insight.component').then(
        (m) => m.FirstInsightComponent,
      ),
  },
  {
    path: 'm',
    canActivate: [nativeAppGuard, mobileAuthGuard],
    loadComponent: () =>
      import('./features/mobile/shell/mobile-shell.component').then((m) => m.MobileShellComponent),
    children: MOBILE_ROUTES,
  },
  // Everything else is the responsive web app, behind one lazy boundary: its
  // chrome and PrimeNG are not part of the initial bundle. See
  // shell/web-shell/web-shell.routes.ts.
  {
    path: '',
    loadChildren: () =>
      import('./shell/web-shell/web-shell.routes').then((m) => m.WEB_SHELL_ROUTES),
  },
  { path: '**', redirectTo: '' },
];
