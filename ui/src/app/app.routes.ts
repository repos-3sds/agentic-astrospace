import { Routes } from '@angular/router';
import { authGuard } from './core/auth.guard';
import { adminGuard } from './core/admin.guard';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/landing/landing.component').then((m) => m.LandingComponent),
  },
  {
    path: 'auth',
    loadComponent: () => import('./features/auth/auth.component').then((m) => m.AuthComponent),
  },
  {
    path: 'app',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
  },
  {
    path: 'settings',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/settings/settings.component').then((m) => m.SettingsComponent),
  },
  {
    path: 'admin',
    canActivate: [adminGuard],
    loadComponent: () =>
      import('./features/admin/admin-console.component').then(
        (m) => m.AdminConsoleComponent,
      ),
  },
  {
    path: 'kundli/:id',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/kundli/kundli-page/kundli-page.component').then(
        (m) => m.KundliPageComponent,
      ),
    children: [
      { path: '', redirectTo: 'overview', pathMatch: 'full' },
      {
        path: 'overview',
        loadComponent: () =>
          import('./features/kundli/overview/overview-tab.component').then(
            (m) => m.OverviewTabComponent,
          ),
      },
      {
        path: 'vedic',
        loadComponent: () =>
          import('./features/kundli/vedic/vedic-tab.component').then((m) => m.VedicTabComponent),
      },
      {
        path: 'varga-charts',
        loadComponent: () =>
          import('./features/kundli/varga-charts/varga-charts-tab.component').then(
            (m) => m.VargaChartsTabComponent,
          ),
      },
      {
        path: 'dashas',
        loadComponent: () =>
          import('./features/kundli/dashas/dashas-tab.component').then(
            (m) => m.DashasTabComponent,
          ),
      },
      {
        path: 'jaimini',
        loadComponent: () =>
          import('./features/kundli/jaimini/jaimini-tab.component').then(
            (m) => m.JaiminiTabComponent,
          ),
      },
      {
        path: 'transits',
        loadComponent: () =>
          import('./features/kundli/transits/transits-tab.component').then(
            (m) => m.TransitsTabComponent,
          ),
      },
      {
        path: 'gocharam',
        loadComponent: () =>
          import('./features/kundli/gocharam/gocharam-tab.component').then(
            (m) => m.GocharamTabComponent,
          ),
      },
      {
        path: 'calendar',
        loadComponent: () =>
          import('./features/kundli/calendar/calendar-tab.component').then(
            (m) => m.CalendarTabComponent,
          ),
      },
      {
        path: 'ashtakavarga',
        loadComponent: () =>
          import('./features/kundli/ashtakavarga/ashtakavarga-tab.component').then(
            (m) => m.AshtakavargaTabComponent,
          ),
      },
      {
        path: 'yogas-doshas',
        loadComponent: () =>
          import('./features/kundli/yogas-doshas/yogas-doshas-tab.component').then(
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
          import('./features/kundli/ask/ask-tab.component').then((m) => m.AskTabComponent),
      },
      {
        path: 'chart',
        loadComponent: () =>
          import('./features/kundli/chart/chart-tab.component').then((m) => m.ChartTabComponent),
      },
      {
        path: 'readings',
        loadComponent: () =>
          import('./features/kundli/readings/readings-tab.component').then(
            (m) => m.ReadingsTabComponent,
          ),
      },
      {
        path: 'compat',
        loadComponent: () =>
          import('./features/kundli/compat/compat-tab.component').then((m) => m.CompatTabComponent),
      },
      {
        path: 'notes',
        loadComponent: () =>
          import('./features/kundli/notes/notes-tab.component').then((m) => m.NotesTabComponent),
      },
    ],
  },
  // Native app screens (Figma RRhuTcaKIhqILZW7JUKFzI). Namespaced under /m so
  // the existing web routes are untouched and both can ship from one bundle.
  {
    path: 'm',
    loadComponent: () =>
      import('./features/mobile/shell/mobile-shell.component').then((m) => m.MobileShellComponent),
    children: [
      { path: '', redirectTo: 'today', pathMatch: 'full' },
      {
        path: 'today',
        loadComponent: () =>
          import('./features/mobile/today/today.component').then((m) => m.TodayComponent),
      },
      {
        path: 'ask',
        loadComponent: () =>
          import('./features/mobile/ask/ask-home.component').then((m) => m.AskHomeComponent),
      },
      {
        path: 'ask/answer',
        loadComponent: () =>
          import('./features/mobile/ask/ask-answer.component').then((m) => m.AskAnswerComponent),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
