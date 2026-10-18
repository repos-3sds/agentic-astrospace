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
    title: 'Today',
    loadComponent: () =>
      import('./today/today.component').then((m) => m.TodayComponent),
  },
  {
    path: 'ask',
    title: 'Ask',
    loadComponent: () =>
      import('./ask/ask-home.component').then((m) => m.AskHomeComponent),
  },
  {
    path: 'ask/history',
    title: 'Past questions',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./ask/ask-history.component').then(
        (m) => m.AskHistoryComponent,
      ),
  },
  {
    path: 'ask/loading',
    title: 'Ask',
    data: { hideMobileTabs: true },
    loadComponent: () => import('./ask/ask-loading.component').then((m) => m.AskLoadingComponent),
  },
  {
    path: 'ask/answer',
    title: 'Answer',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./ask/ask-answer.component').then((m) => m.AskAnswerComponent),
  },
  {
    path: 'ask/refer',
    title: 'Ask a professional',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./ask/ask-refer-out.component').then(
        (m) => m.AskReferOutComponent,
      ),
  },
  {
    path: 'family',
    title: 'Family',
    loadComponent: () =>
      import('./family/family.component').then((m) => m.FamilyComponent),
  },
  {
    path: 'explore',
    title: 'Explore',
    loadComponent: () =>
      import('./explore/explore-menu.component').then(
        (m) => m.ExploreMenuComponent,
      ),
  },
  {
    path: 'explore/library',
    title: 'Library',
    loadComponent: () =>
      import('./explore/guided-explore.component').then(
        (m) => m.GuidedExploreComponent,
      ),
  },
  {
    path: 'explore/story',
    title: 'Your story',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./explore/guided-story.component').then(
        (m) => m.GuidedStoryComponent,
      ),
  },
  {
    path: 'explore/what-to-do',
    title: 'What to do',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./remedies/remedies.component').then(
        (m) => m.RemediesComponent,
      ),
  },
  {
    path: 'explore/life-chapters',
    title: 'Life chapters',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./explore/guided-life-chapters.component').then(
        (m) => m.GuidedLifeChaptersComponent,
      ),
  },
  {
    path: 'remedies',
    title: 'Remedies',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./remedies/remedies.component').then(
        (m) => m.RemediesComponent,
      ),
  },
  {
    path: 'remedies/mantra',
    title: 'Mantra',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./remedies/mantra-tracker.component').then(
        (m) => m.MantraTrackerComponent,
      ),
  },
  {
    path: 'muhurta',
    title: 'Muhurtas',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./muhurta/muhurta-goal.component').then(
        (m) => m.MuhurtaGoalComponent,
      ),
  },
  {
    path: 'muhurta/results',
    title: 'Good times',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./muhurta/muhurta-results.component').then(
        (m) => m.MuhurtaResultsComponent,
      ),
  },
  {
    path: 'chart',
    title: 'Your chart',
    loadComponent: () =>
      import('./chart/chart-hub.component').then(
        (m) => m.ChartHubComponent,
      ),
  },
  {
    path: 'chart/full',
    title: 'Full chart',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./chart/chart-full.component').then(
        (m) => m.ChartFullComponent,
      ),
  },
  {
    path: 'chart/vargas',
    title: 'Divisional charts',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./chart/varga-charts.component').then(
        (m) => m.VargaChartsComponent,
      ),
  },
  {
    path: 'chart/birth-details',
    title: 'Birth details',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./chart/birth-details-screen.component').then(
        (m) => m.BirthDetailsScreenComponent,
      ),
  },
  {
    path: 'chart/reference',
    title: 'Chart reference',
    data: { referenceMode: 'home', hideMobileTabs: true },
    loadComponent: () => import('./chart/reference.component').then((m) => m.ReferenceComponent),
  },
  {
    path: 'chart/reference/avkahada',
    title: 'Avakahada',
    data: { referenceMode: 'avkahada', hideMobileTabs: true },
    loadComponent: () => import('./chart/reference.component').then((m) => m.ReferenceComponent),
  },
  {
    path: 'chart/reference/grahas',
    title: 'Planets',
    data: { referenceMode: 'grahas', hideMobileTabs: true },
    loadComponent: () => import('./chart/reference.component').then((m) => m.ReferenceComponent),
  },
  {
    path: 'chart/reference/ashtakavarga',
    title: 'Ashtakavarga',
    data: { referenceMode: 'ashtakavarga', hideMobileTabs: true },
    loadComponent: () => import('./chart/reference.component').then((m) => m.ReferenceComponent),
  },
  {
    path: 'chart/reference/favourable',
    title: 'Favourable points',
    data: { referenceMode: 'favourable', hideMobileTabs: true },
    loadComponent: () => import('./chart/reference.component').then((m) => m.ReferenceComponent),
  },
  {
    path: 'chart/periods',
    title: 'Life periods',
    loadComponent: () =>
      import('./chart/life-periods.component').then(
        (m) => m.LifePeriodsComponent,
      ),
  },
  {
    path: 'chart/yogas',
    title: 'Yogas and doshas',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./chart/yogas-doshas.component').then(
        (m) => m.YogasDoshasComponent,
      ),
  },
  {
    path: 'chart/strength',
    title: 'Planet strength',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./chart/strength-advanced.component').then(
        (m) => m.StrengthAdvancedComponent,
      ),
  },
  {
    path: 'settings',
    title: 'Settings',
    loadComponent: () =>
      import('./settings/settings-home.component').then(
        (m) => m.SettingsHomeComponent,
      ),
  },
  {
    path: 'settings/profiles',
    title: 'Profiles',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/profile-management.component').then(
        (m) => m.ProfileManagementComponent,
      ),
  },
  {
    path: 'settings/profiles/new',
    title: 'New profile',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/profile-form.component').then(
        (m) => m.ProfileFormComponent,
      ),
  },
  {
    path: 'settings/profiles/:id/edit',
    title: 'Edit profile',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/profile-form.component').then(
        (m) => m.ProfileFormComponent,
      ),
  },
  {
    path: 'settings/profiles/:id/memory',
    title: 'What Siddha remembers',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/profile-memory.component').then(
        (m) => m.ProfileMemoryComponent,
      ),
  },
  {
    path: 'settings/profiles/:id/delete',
    title: 'Delete profile',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/profile-delete.component').then(
        (m) => m.ProfileDeleteComponent,
      ),
  },
  {
    path: 'settings/birth-details',
    title: 'Birth details',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/edit-birth-details.component').then(
        (m) => m.EditBirthDetailsComponent,
      ),
  },
  {
    path: 'settings/mode',
    title: 'Experience',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/mode-tone.component').then(
        (m) => m.ModeToneComponent,
      ),
  },
  {
    path: 'settings/appearance',
    title: 'Appearance',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/appearance.component').then(
        (m) => m.AppearanceComponent,
      ),
  },
  {
    path: 'settings/language',
    title: 'Language',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/language-audio.component').then(
        (m) => m.LanguageAudioComponent,
      ),
  },
  {
    path: 'settings/notifications',
    title: 'Notifications',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/notifications.component').then(
        (m) => m.NotificationsComponent,
      ),
  },
  {
    path: 'subhashita',
    title: 'Today’s Subhashita',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./subhashita/subhashita.component').then(
        (m) => m.SubhashitaComponent,
      ),
  },
  {
    path: 'settings/interaction',
    title: 'Interaction',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/interaction.component').then(
        (m) => m.InteractionComponent,
      ),
  },
  {
    path: 'settings/location',
    title: 'Location',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/location.component').then(
        (m) => m.LocationComponent,
      ),
  },
  {
    path: 'settings/festivals',
    title: 'Festivals',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/festival-preferences.component').then(
        (m) => m.FestivalPreferencesComponent,
      ),
  },
  {
    path: 'settings/account',
    title: 'Account',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/account-privacy.component').then(
        (m) => m.AccountPrivacyComponent,
      ),
  },
  {
    path: 'settings/account/delete',
    title: 'Delete account',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/account-deletion.component').then(
        (m) => m.AccountDeletionComponent,
      ),
  },
  {
    path: 'settings/conventions',
    title: 'Conventions',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./settings/conventions.component').then(
        (m) => m.ConventionsComponent,
      ),
  },
  {
    path: 'search',
    title: 'Search',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./utility/search.component').then(
        (m) => m.SearchComponent,
      ),
  },
  {
    path: 'notifications',
    title: 'Notifications',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./utility/notification-center.component').then(
        (m) => m.NotificationCenterComponent,
      ),
  },
  {
    path: 'subscription',
    title: 'Plans',
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
    title: 'Calendar',
    loadComponent: () =>
      import('./calendar/calendar.component').then(
        (m) => m.CalendarComponent,
      ),
  },
  {
    path: 'calendar/day',
    title: 'Day',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./calendar/calendar-day.component').then(
        (m) => m.CalendarDayComponent,
      ),
  },
  {
    path: 'compat',
    title: 'Compatibility',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./compat/compat-hub.component').then(
        (m) => m.CompatHubComponent,
      ),
  },
  {
    path: 'compat/add',
    title: 'Add a person',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./compat/add-prospect.component').then(
        (m) => m.AddProspectComponent,
      ),
  },
  {
    path: 'compat/results',
    title: 'Compatibility',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./compat/compat-results.component').then(
        (m) => m.CompatResultsComponent,
      ),
  },
  {
    path: 'compat/results/detail',
    title: 'Compatibility detail',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./compat/compat-detail.component').then(
        (m) => m.CompatDetailComponent,
      ),
  },
  {
    path: 'transits',
    title: 'Transits',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./transits/gochara.component').then(
        (m) => m.GocharaComponent,
      ),
  },
  {
    path: 'transits/full',
    title: 'All transits',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./transits/full-transits.component').then(
        (m) => m.FullTransitsComponent,
      ),
  },
  {
    path: 'readings',
    title: 'Readings',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./readings/readings.component').then(
        (m) => m.ReadingsComponent,
      ),
  },
  {
    path: 'readings/accuracy',
    title: 'Reading accuracy',
    data: { hideMobileTabs: true },
    loadComponent: () =>
      import('./readings/accuracy.component').then(
        (m) => m.AccuracyComponent,
      ),
  },
  {
    path: 'notes',
    title: 'Notes',
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
