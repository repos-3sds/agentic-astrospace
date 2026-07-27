import { Routes } from '@angular/router';
import { authGuard } from './core/auth.guard';
import { adminGuard } from './core/admin.guard';
import { nativeAppGuard } from './core/native-app.guard';
import { mobileAuthGuard } from './core/mobile-auth.guard';

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
  // Onboarding sits outside the shell — no tab bar until there is an app to
  // navigate. These must precede the 'm' route below: that route's child '**'
  // would otherwise swallow every path under /m and redirect it to today.
  {
    path: 'm/start',
    canActivate: [nativeAppGuard],
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
    path: 'm/language',
    canActivate: [nativeAppGuard],
    loadComponent: () =>
      import('./features/mobile/onboarding/language.component').then((m) => m.LanguageComponent),
  },
  {
    path: 'm/welcome',
    canActivate: [nativeAppGuard],
    loadComponent: () =>
      import('./features/mobile/onboarding/welcome.component').then((m) => m.WelcomeComponent),
  },
  {
    path: 'm/disclaimers',
    canActivate: [nativeAppGuard],
    loadComponent: () =>
      import('./features/mobile/onboarding/disclaimers.component').then(
        (m) => m.DisclaimersComponent,
      ),
  },
  {
    path: 'm/persona',
    canActivate: [nativeAppGuard],
    loadComponent: () =>
      import('./features/mobile/onboarding/persona.component').then((m) => m.PersonaComponent),
  },
  {
    path: 'm/birth-details',
    canActivate: [nativeAppGuard],
    loadComponent: () =>
      import('./features/mobile/onboarding/birth-details.component').then(
        (m) => m.BirthDetailsComponent,
      ),
  },
  {
    path: 'm',
    canActivate: [nativeAppGuard, mobileAuthGuard],
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
        path: 'ask/history',
        loadComponent: () =>
          import('./features/mobile/ask/ask-history.component').then(
            (m) => m.AskHistoryComponent,
          ),
      },
      {
        path: 'ask/answer',
        loadComponent: () =>
          import('./features/mobile/ask/ask-answer.component').then((m) => m.AskAnswerComponent),
      },
      {
        path: 'ask/refer',
        loadComponent: () =>
          import('./features/mobile/ask/ask-refer-out.component').then(
            (m) => m.AskReferOutComponent,
          ),
      },
      {
        path: 'remedies',
        loadComponent: () =>
          import('./features/mobile/remedies/remedies.component').then(
            (m) => m.RemediesComponent,
          ),
      },
      {
        path: 'remedies/mantra',
        loadComponent: () =>
          import('./features/mobile/remedies/mantra-tracker.component').then(
            (m) => m.MantraTrackerComponent,
          ),
      },
      {
        path: 'muhurta',
        loadComponent: () =>
          import('./features/mobile/muhurta/muhurta-goal.component').then(
            (m) => m.MuhurtaGoalComponent,
          ),
      },
      {
        path: 'muhurta/results',
        loadComponent: () =>
          import('./features/mobile/muhurta/muhurta-results.component').then(
            (m) => m.MuhurtaResultsComponent,
          ),
      },
      {
        path: 'chart',
        loadComponent: () =>
          import('./features/mobile/chart/chart-hub.component').then(
            (m) => m.ChartHubComponent,
          ),
      },
      {
        path: 'chart/full',
        loadComponent: () =>
          import('./features/mobile/chart/chart-full.component').then(
            (m) => m.ChartFullComponent,
          ),
      },
      {
        path: 'chart/vargas',
        data: { hideMobileTabs: true },
        loadComponent: () =>
          import('./features/mobile/chart/varga-charts.component').then(
            (m) => m.VargaChartsComponent,
          ),
      },
      {
        path: 'chart/periods',
        data: { hideMobileTabs: true },
        loadComponent: () =>
          import('./features/mobile/chart/life-periods.component').then(
            (m) => m.LifePeriodsComponent,
          ),
      },
      {
        path: 'chart/yogas',
        data: { hideMobileTabs: true },
        loadComponent: () =>
          import('./features/mobile/chart/yogas-doshas.component').then(
            (m) => m.YogasDoshasComponent,
          ),
      },
      {
        path: 'chart/strength',
        data: { hideMobileTabs: true },
        loadComponent: () =>
          import('./features/mobile/chart/strength-advanced.component').then(
            (m) => m.StrengthAdvancedComponent,
          ),
      },
      {
        path: 'settings',
        loadComponent: () =>
          import('./features/mobile/settings/settings-home.component').then(
            (m) => m.SettingsHomeComponent,
          ),
      },
      {
        path: 'settings/mode',
        loadComponent: () =>
          import('./features/mobile/settings/mode-tone.component').then(
            (m) => m.ModeToneComponent,
          ),
      },
      {
        path: 'settings/language',
        loadComponent: () =>
          import('./features/mobile/settings/language-audio.component').then(
            (m) => m.LanguageAudioComponent,
          ),
      },
      {
        path: 'settings/notifications',
        loadComponent: () =>
          import('./features/mobile/settings/notifications.component').then(
            (m) => m.NotificationsComponent,
          ),
      },
      {
        path: 'settings/location',
        loadComponent: () =>
          import('./features/mobile/settings/location.component').then(
            (m) => m.LocationComponent,
          ),
      },
      {
        path: 'settings/account',
        loadComponent: () =>
          import('./features/mobile/settings/account-privacy.component').then(
            (m) => m.AccountPrivacyComponent,
          ),
      },
      {
        path: 'settings/conventions',
        loadComponent: () =>
          import('./features/mobile/settings/conventions.component').then(
            (m) => m.ConventionsComponent,
          ),
      },
      // Calendar, compatibility, transits, readings and notes are kept in one
      // contiguous ownership block so parallel feature work rebases cleanly.
      {
        path: 'calendar',
        loadComponent: () =>
          import('./features/mobile/calendar/calendar.component').then(
            (m) => m.CalendarComponent,
          ),
      },
      {
        path: 'calendar/day',
        data: { hideMobileTabs: true },
        loadComponent: () =>
          import('./features/mobile/calendar/calendar-day.component').then(
            (m) => m.CalendarDayComponent,
          ),
      },
      {
        path: 'compat',
        data: { hideMobileTabs: true },
        loadComponent: () =>
          import('./features/mobile/compat/compat-hub.component').then(
            (m) => m.CompatHubComponent,
          ),
      },
      {
        path: 'compat/add',
        data: { hideMobileTabs: true },
        loadComponent: () =>
          import('./features/mobile/compat/add-prospect.component').then(
            (m) => m.AddProspectComponent,
          ),
      },
      {
        path: 'compat/results',
        data: { hideMobileTabs: true },
        loadComponent: () =>
          import('./features/mobile/compat/compat-results.component').then(
            (m) => m.CompatResultsComponent,
          ),
      },
      {
        path: 'transits',
        data: { hideMobileTabs: true },
        loadComponent: () =>
          import('./features/mobile/transits/gochara.component').then(
            (m) => m.GocharaComponent,
          ),
      },
      {
        path: 'transits/full',
        data: { hideMobileTabs: true },
        loadComponent: () =>
          import('./features/mobile/transits/full-transits.component').then(
            (m) => m.FullTransitsComponent,
          ),
      },
      {
        path: 'readings',
        data: { hideMobileTabs: true },
        loadComponent: () =>
          import('./features/mobile/readings/readings.component').then(
            (m) => m.ReadingsComponent,
          ),
      },
      {
        path: 'readings/accuracy',
        data: { hideMobileTabs: true },
        loadComponent: () =>
          import('./features/mobile/readings/accuracy.component').then(
            (m) => m.AccuracyComponent,
          ),
      },
      {
        path: 'notes',
        data: { hideMobileTabs: true },
        loadComponent: () =>
          import('./features/mobile/notes/notes.component').then(
            (m) => m.NotesComponent,
          ),
      },
      // The tab bar has five tabs and three of them are not built yet. Without
      // this they fall through to the global '**' below and land on the web
      // app's marketing page — in the native build that reads as the app
      // crashing out of itself, with no way back but force-quitting.
      { path: '**', redirectTo: 'today' },
    ],
  },
  { path: '**', redirectTo: '' },
];
