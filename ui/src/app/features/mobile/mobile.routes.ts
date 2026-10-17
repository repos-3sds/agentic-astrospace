import { Routes } from '@angular/router';

/**
 * The native app's screens, mounted under `/m` by app.routes.ts (which owns
 * the shell component and the guards). Kept apart from the web app's routes
 * so the two front ends can be read, and reviewed, on their own.
 */
export const MOBILE_ROUTES: Routes = [
  { path: '', redirectTo: 'today', pathMatch: 'full' },
  {
    path: 'today',
    loadComponent: () =>
      import('./today/today.component').then((m) => m.TodayComponent),
  },
  {
    path: 'ask',
    loadComponent: () =>
      import('./ask/ask-home.component').then((m) => m.AskHomeComponent),
  },
  {
    path: 'ask/history',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./ask/ask-history.component').then(
        (m) => m.AskHistoryComponent,
      ),
  },
  {
    path: 'ask/loading',
    data: { hideMobileTabs: true },
    loadComponent: () => import('./ask/ask-loading.component').then((m) => m.AskLoadingComponent),
  },
  {
    path: 'ask/answer',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./ask/ask-answer.component').then((m) => m.AskAnswerComponent),
  },
  {
    path: 'ask/refer',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./ask/ask-refer-out.component').then(
        (m) => m.AskReferOutComponent,
      ),
  },
  {
    path: 'family',
    loadComponent: () =>
      import('./family/family.component').then((m) => m.FamilyComponent),
  },
  {
    path: 'explore',
    loadComponent: () =>
      import('./explore/explore-menu.component').then(
        (m) => m.ExploreMenuComponent,
      ),
  },
  {
    path: 'explore/library',
    loadComponent: () =>
      import('./explore/guided-explore.component').then(
        (m) => m.GuidedExploreComponent,
      ),
  },
  {
    path: 'explore/story',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./explore/guided-story.component').then(
        (m) => m.GuidedStoryComponent,
      ),
  },
  {
    path: 'explore/what-to-do',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./remedies/remedies.component').then(
        (m) => m.RemediesComponent,
      ),
  },
  {
    path: 'explore/life-chapters',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./explore/guided-life-chapters.component').then(
        (m) => m.GuidedLifeChaptersComponent,
      ),
  },
  {
    path: 'remedies',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./remedies/remedies.component').then(
        (m) => m.RemediesComponent,
      ),
  },
  {
    path: 'remedies/mantra',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./remedies/mantra-tracker.component').then(
        (m) => m.MantraTrackerComponent,
      ),
  },
  {
    path: 'muhurta',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./muhurta/muhurta-goal.component').then(
        (m) => m.MuhurtaGoalComponent,
      ),
  },
  {
    path: 'muhurta/results',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./muhurta/muhurta-results.component').then(
        (m) => m.MuhurtaResultsComponent,
      ),
  },
  {
    path: 'chart',
    loadComponent: () =>
      import('./chart/chart-hub.component').then(
        (m) => m.ChartHubComponent,
      ),
  },
  {
    path: 'chart/full',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./chart/chart-full.component').then(
        (m) => m.ChartFullComponent,
      ),
  },
  {
    path: 'chart/vargas',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./chart/varga-charts.component').then(
        (m) => m.VargaChartsComponent,
      ),
  },
  {
    path: 'chart/birth-details',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./chart/birth-details-screen.component').then(
        (m) => m.BirthDetailsScreenComponent,
      ),
  },
  {
    path: 'chart/reference',
    data: { referenceMode: 'home', hideMobileTabs: true },
    loadComponent: () => import('./chart/reference.component').then((m) => m.ReferenceComponent),
  },
  {
    path: 'chart/reference/avkahada',
    data: { referenceMode: 'avkahada', hideMobileTabs: true },
    loadComponent: () => import('./chart/reference.component').then((m) => m.ReferenceComponent),
  },
  {
    path: 'chart/reference/grahas',
    data: { referenceMode: 'grahas', hideMobileTabs: true },
    loadComponent: () => import('./chart/reference.component').then((m) => m.ReferenceComponent),
  },
  {
    path: 'chart/reference/ashtakavarga',
    data: { referenceMode: 'ashtakavarga', hideMobileTabs: true },
    loadComponent: () => import('./chart/reference.component').then((m) => m.ReferenceComponent),
  },
  {
    path: 'chart/reference/favourable',
    data: { referenceMode: 'favourable', hideMobileTabs: true },
    loadComponent: () => import('./chart/reference.component').then((m) => m.ReferenceComponent),
  },
  {
    path: 'chart/periods',
    loadComponent: () =>
      import('./chart/life-periods.component').then(
        (m) => m.LifePeriodsComponent,
      ),
  },
  {
    path: 'chart/yogas',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./chart/yogas-doshas.component').then(
        (m) => m.YogasDoshasComponent,
      ),
  },
  {
    path: 'chart/strength',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./chart/strength-advanced.component').then(
        (m) => m.StrengthAdvancedComponent,
      ),
  },
  {
    path: 'settings',
    loadComponent: () =>
      import('./settings/settings-home.component').then(
        (m) => m.SettingsHomeComponent,
      ),
  },
  {
    path: 'settings/profiles',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/profile-management.component').then(
        (m) => m.ProfileManagementComponent,
      ),
  },
  {
    path: 'settings/profiles/new',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/profile-form.component').then(
        (m) => m.ProfileFormComponent,
      ),
  },
  {
    path: 'settings/profiles/:id/edit',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/profile-form.component').then(
        (m) => m.ProfileFormComponent,
      ),
  },
  {
    path: 'settings/profiles/:id/memory',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/profile-memory.component').then(
        (m) => m.ProfileMemoryComponent,
      ),
  },
  {
    path: 'settings/profiles/:id/delete',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/profile-delete.component').then(
        (m) => m.ProfileDeleteComponent,
      ),
  },
  {
    path: 'settings/birth-details',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/edit-birth-details.component').then(
        (m) => m.EditBirthDetailsComponent,
      ),
  },
  {
    path: 'settings/mode',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/mode-tone.component').then(
        (m) => m.ModeToneComponent,
      ),
  },
  {
    path: 'settings/appearance',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/appearance.component').then(
        (m) => m.AppearanceComponent,
      ),
  },
  {
    path: 'settings/language',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/language-audio.component').then(
        (m) => m.LanguageAudioComponent,
      ),
  },
  {
    path: 'settings/notifications',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/notifications.component').then(
        (m) => m.NotificationsComponent,
      ),
  },
  {
    path: 'subhashita',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./subhashita/subhashita.component').then(
        (m) => m.SubhashitaComponent,
      ),
  },
  {
    path: 'settings/interaction',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/interaction.component').then(
        (m) => m.InteractionComponent,
      ),
  },
  {
    path: 'settings/location',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/location.component').then(
        (m) => m.LocationComponent,
      ),
  },
  {
    path: 'settings/festivals',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/festival-preferences.component').then(
        (m) => m.FestivalPreferencesComponent,
      ),
  },
  {
    path: 'settings/account',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/account-privacy.component').then(
        (m) => m.AccountPrivacyComponent,
      ),
  },
  {
    path: 'settings/account/delete',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/account-deletion.component').then(
        (m) => m.AccountDeletionComponent,
      ),
  },
  {
    path: 'settings/conventions',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/conventions.component').then(
        (m) => m.ConventionsComponent,
      ),
  },
  {
    path: 'search',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./utility/search.component').then(
        (m) => m.SearchComponent,
      ),
  },
  {
    path: 'notifications',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./utility/notification-center.component').then(
        (m) => m.NotificationCenterComponent,
      ),
  },
  {
    path: 'subscription',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./utility/subscription.component').then(
        (m) => m.SubscriptionComponent,
      ),
  },
  // Calendar, compatibility, transits, readings and notes are kept in one
  // contiguous ownership block so parallel feature work rebases cleanly.
  {
    path: 'calendar',
    loadComponent: () =>
      import('./calendar/calendar.component').then(
        (m) => m.CalendarComponent,
      ),
  },
  {
    path: 'calendar/day',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./calendar/calendar-day.component').then(
        (m) => m.CalendarDayComponent,
      ),
  },
  {
    path: 'compat',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./compat/compat-hub.component').then(
        (m) => m.CompatHubComponent,
      ),
  },
  {
    path: 'compat/add',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./compat/add-prospect.component').then(
        (m) => m.AddProspectComponent,
      ),
  },
  {
    path: 'compat/results',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./compat/compat-results.component').then(
        (m) => m.CompatResultsComponent,
      ),
  },
  {
    path: 'compat/results/detail',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./compat/compat-detail.component').then(
        (m) => m.CompatDetailComponent,
      ),
  },
  {
    path: 'transits',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./transits/gochara.component').then(
        (m) => m.GocharaComponent,
      ),
  },
  {
    path: 'transits/full',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./transits/full-transits.component').then(
        (m) => m.FullTransitsComponent,
      ),
  },
  {
    path: 'readings',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./readings/readings.component').then(
        (m) => m.ReadingsComponent,
      ),
  },
  {
    path: 'readings/accuracy',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./readings/accuracy.component').then(
        (m) => m.AccuracyComponent,
      ),
  },
  {
    path: 'notes',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./notes/notes.component').then(
        (m) => m.NotesComponent,
      ),
  },
  // The tab bar has five tabs and three of them are not built yet. Without
  // this they fall through to the global '**' below and land on the web
  // app's marketing page — in the native build that reads as the app
  // crashing out of itself, with no way back but force-quitting.
  { path: '**', redirectTo: 'today' },
];
