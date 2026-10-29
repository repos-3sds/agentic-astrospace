import { appLinkRoute } from './app-links.service';

describe('appLinkRoute', () => {
  it('opens the screens emails link to', () => {
    expect(appLinkRoute('https://asksiddha.app/m/today')).toBe('/m/today');
    expect(appLinkRoute('https://asksiddha.app/m/calendar/')).toBe('/m/calendar');
    expect(appLinkRoute('https://www.asksiddha.app/m/settings?utm=x')).toBe('/m/settings');
    expect(appLinkRoute('https://asksiddha.app/m/chart/periods')).toBe('/m/chart/periods');
    expect(appLinkRoute('https://asksiddha.app/m/compat')).toBe('/m/compat');
  });

  it('keeps only a plain date on Calendar\'s day view', () => {
    expect(appLinkRoute('https://asksiddha.app/m/calendar/day?date=2026-11-08')).toBe('/m/calendar/day?date=2026-11-08');
    expect(appLinkRoute('https://asksiddha.app/m/calendar/day?date=tomorrow')).toBe('/m/calendar/day');
    expect(appLinkRoute('https://asksiddha.app/m/today?date=2026-11-08')).toBe('/m/today');
  });

  it('ignores other hosts, schemes and screens', () => {
    expect(appLinkRoute('https://evil.example/m/today')).toBeNull();
    expect(appLinkRoute('http://asksiddha.app/m/today')).toBeNull();
    expect(appLinkRoute('https://asksiddha.app/m/account/delete')).toBeNull();
    expect(appLinkRoute('https://asksiddha.app/')).toBeNull();
    expect(appLinkRoute('app.asksiddha.mobile://auth/callback')).toBeNull();
    expect(appLinkRoute('not a url')).toBeNull();
    expect(appLinkRoute(undefined)).toBeNull();
  });
});
