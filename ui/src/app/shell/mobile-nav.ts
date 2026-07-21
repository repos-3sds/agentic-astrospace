export interface AppNavItem {
  route: string;
  label: string;
  icon: string;
  requiresProfile?: boolean;
}

export const GLOBAL_PRIMARY_NAV: AppNavItem[] = [
  { route: 'home', label: 'Home', icon: 'layout-dashboard' },
  { route: 'profiles', label: 'Profiles', icon: 'users' },
  { route: 'ask', label: 'Ask AI', icon: 'message-circle', requiresProfile: true },
  { route: 'settings', label: 'Settings', icon: 'settings' },
];

export const PROFILE_PRIMARY_NAV: AppNavItem[] = [
  { route: 'overview', label: 'Today', icon: 'layout-dashboard', requiresProfile: true },
  { route: 'chart', label: 'Chart', icon: 'sparkles', requiresProfile: true },
  { route: 'dashas', label: 'Timeline', icon: 'calendar-days', requiresProfile: true },
  { route: 'ask', label: 'Ask', icon: 'message-circle', requiresProfile: true },
];

export const KUNDLI_MORE_NAV: AppNavItem[] = [
  { route: 'vedic', label: 'Vedic Details', icon: 'sparkles', requiresProfile: true },
  { route: 'varga-charts', label: 'Varga Charts', icon: 'layout-dashboard', requiresProfile: true },
  { route: 'calendar', label: 'Calendar & Panchanga', icon: 'calendar-days', requiresProfile: true },
  { route: 'jaimini', label: 'Jaimini', icon: 'sparkles', requiresProfile: true },
  { route: 'transits', label: 'Transits', icon: 'sparkles', requiresProfile: true },
  { route: 'gocharam', label: 'Gocharam', icon: 'sparkles', requiresProfile: true },
  { route: 'ashtakavarga', label: 'Ashtakavarga', icon: 'layout-dashboard', requiresProfile: true },
  { route: 'yogas-doshas', label: 'Yogas & Doshas', icon: 'sparkles', requiresProfile: true },
  { route: 'compat', label: 'Compatibility', icon: 'users', requiresProfile: true },
  { route: 'readings', label: 'Readings', icon: 'message-circle', requiresProfile: true },
  { route: 'notes', label: 'Notes', icon: 'message-circle', requiresProfile: true },
];

export const ACCOUNT_NAV: AppNavItem[] = [
  { route: 'settings', label: 'Settings', icon: 'settings' },
];

export const ROUTE_TITLES: Record<string, string> = {
  home: 'Home',
  profiles: 'Profiles',
  overview: 'Today',
  vedic: 'Vedic Details',
  'varga-charts': 'Varga Charts',
  dashas: 'Timeline',
  jaimini: 'Jaimini',
  transits: 'Transits',
  gocharam: 'Gocharam',
  calendar: 'Calendar',
  ashtakavarga: 'Ashtakavarga',
  'yogas-doshas': 'Yogas & Doshas',
  chart: 'Chart',
  readings: 'Readings',
  compat: 'Compatibility',
  notes: 'Notes',
  ask: 'Ask AI',
  settings: 'Settings',
};
