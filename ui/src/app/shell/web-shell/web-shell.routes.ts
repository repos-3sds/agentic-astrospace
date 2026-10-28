import { inject, provideEnvironmentInitializer } from '@angular/core';
import { Routes } from '@angular/router';
import { ConfirmationService, MessageService } from 'primeng/api';
import { PrimeNG } from 'primeng/config';

import { adminGuard } from '../../core/admin.guard';
import { authGuard, webLandingGuard } from '../../core/auth.guard';
import { CelestialPreset } from '../../theme';
import { WebShellComponent } from './web-shell.component';

/**
 * Every route of the responsive web app, behind one lazy boundary so that
 * PrimeNG and the web chrome are parsed only when one of them is visited.
 * The native app (/m) never loads this file.
 *
 * PrimeNG is configured here rather than with a global providePrimeNG():
 * that helper registers an *app* initializer, which a lazily created route
 * injector never runs. PrimeNG's config service is root-scoped and applies a
 * theme whenever it is set, so setting it as this injector is created is
 * equivalent.
 */
export const WEB_SHELL_ROUTES: Routes = [
  {
    path: '',
    component: WebShellComponent,
    providers: [
      MessageService,
      ConfirmationService,
      provideEnvironmentInitializer(() => {
        inject(PrimeNG).setConfig({
          theme: {
            preset: CelestialPreset,
            options: {
              darkModeSelector: '.app-dark',
            },
          },
        });
      }),
    ],
    children: [
      {
        path: '',
        pathMatch: 'full',
        canActivate: [webLandingGuard],
        loadComponent: () =>
          import('../../features/landing/landing.component').then((m) => m.LandingComponent),
      },
      {
        path: 'auth',
        loadComponent: () => import('../../features/auth/auth.component').then((m) => m.AuthComponent),
      },
      {
        path: 'app',
        canActivate: [authGuard],
        loadComponent: () =>
          import('../../features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
      },
      {
        path: 'settings',
        canActivate: [authGuard],
        loadComponent: () =>
          import('../../features/settings/settings.component').then((m) => m.SettingsComponent),
      },
      {
        path: 'admin',
        canActivate: [adminGuard],
        loadComponent: () =>
          import('../../features/admin/admin-console.component').then(
            (m) => m.AdminConsoleComponent,
          ),
      },
      {
        path: 'ask/:id',
        canActivate: [authGuard],
        loadComponent: () =>
          import('../../features/kundli/ask/ask-tab.component').then((m) => m.AskTabComponent),
        children: [
          { path: '', pathMatch: 'full', loadComponent: () => import('../../features/mobile/ask/ask-home.component').then(m => m.AskHomeComponent) },
          { path: 'answer', loadComponent: () => import('../../features/mobile/ask/ask-answer.component').then(m => m.AskAnswerComponent) },
          { path: 'history', loadComponent: () => import('../../features/mobile/ask/ask-history.component').then(m => m.AskHistoryComponent) },
          { path: 'refer', loadComponent: () => import('../../features/mobile/ask/ask-refer-out.component').then(m => m.AskReferOutComponent) },
          { path: 'memory', data: { backToAsk: true }, loadComponent: () => import('../../features/mobile/settings/profile-memory.component').then(m => m.ProfileMemoryComponent) },
        ],
      },
      {
        path: 'kundli/:id',
        canActivate: [authGuard],
        loadComponent: () =>
          import('../../features/kundli/kundli-page/kundli-page.component').then(
            (m) => m.KundliPageComponent,
          ),
        children: [
          { path: '', redirectTo: 'overview', pathMatch: 'full' },
          {
            path: 'overview',
            loadComponent: () =>
              import('../../features/kundli/overview/overview-tab.component').then(
                (m) => m.OverviewTabComponent,
              ),
          },
          {
            path: 'vedic',
            loadComponent: () =>
              import('../../features/kundli/vedic/vedic-tab.component').then((m) => m.VedicTabComponent),
          },
          {
            path: 'varga-charts',
            loadComponent: () =>
              import('../../features/kundli/varga-charts/varga-charts-tab.component').then(
                (m) => m.VargaChartsTabComponent,
              ),
          },
          {
            path: 'dashas',
            loadComponent: () =>
              import('../../features/kundli/dashas/dashas-tab.component').then(
                (m) => m.DashasTabComponent,
              ),
          },
          {
            path: 'jaimini',
            loadComponent: () =>
              import('../../features/kundli/jaimini/jaimini-tab.component').then(
                (m) => m.JaiminiTabComponent,
              ),
          },
          {
            path: 'transits',
            loadComponent: () =>
              import('../../features/kundli/transits/transits-tab.component').then(
                (m) => m.TransitsTabComponent,
              ),
          },
          {
            path: 'gocharam',
            loadComponent: () =>
              import('../../features/kundli/gocharam/gocharam-tab.component').then(
                (m) => m.GocharamTabComponent,
              ),
          },
          {
            path: 'calendar',
            loadComponent: () =>
              import('../../features/kundli/calendar/calendar-tab.component').then(
                (m) => m.CalendarTabComponent,
              ),
          },
          {
            path: 'ashtakavarga',
            loadComponent: () =>
              import('../../features/kundli/ashtakavarga/ashtakavarga-tab.component').then(
                (m) => m.AshtakavargaTabComponent,
              ),
          },
          {
            path: 'yogas-doshas',
            loadComponent: () =>
              import('../../features/kundli/yogas-doshas/yogas-doshas-tab.component').then(
                (m) => m.YogasDoshasTabComponent,
              ),
          },
          {
            path: 'today',
            redirectTo: 'calendar',
            pathMatch: 'full',
          },
          {
            path: 'ask',
            loadComponent: () =>
              import('../../features/kundli/ask/ask-tab.component').then((m) => m.AskTabComponent),
            children: [
              { path: '', pathMatch: 'full', loadComponent: () => import('../../features/mobile/ask/ask-home.component').then(m => m.AskHomeComponent) },
              { path: 'answer', loadComponent: () => import('../../features/mobile/ask/ask-answer.component').then(m => m.AskAnswerComponent) },
              { path: 'history', loadComponent: () => import('../../features/mobile/ask/ask-history.component').then(m => m.AskHistoryComponent) },
              { path: 'refer', loadComponent: () => import('../../features/mobile/ask/ask-refer-out.component').then(m => m.AskReferOutComponent) },
              { path: 'memory', data: { backToAsk: true }, loadComponent: () => import('../../features/mobile/settings/profile-memory.component').then(m => m.ProfileMemoryComponent) },
            ],
          },
          {
            path: 'chart',
            loadComponent: () =>
              import('../../features/kundli/chart/chart-tab.component').then((m) => m.ChartTabComponent),
          },
          {
            path: 'readings',
            loadComponent: () =>
              import('../../features/kundli/readings/readings-tab.component').then(
                (m) => m.ReadingsTabComponent,
              ),
          },
          {
            path: 'compat',
            loadComponent: () =>
              import('../../features/kundli/compat/compat-tab.component').then((m) => m.CompatTabComponent),
          },
          {
            path: 'notes',
            loadComponent: () =>
              import('../../features/kundli/notes/notes-tab.component').then((m) => m.NotesTabComponent),
          },
        ],
      },
    ],
  },
];
