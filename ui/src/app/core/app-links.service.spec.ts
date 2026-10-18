import { appLinkRoute } from './app-links.service';

describe('appLinkRoute', () => {
  it('opens the screens emails link to', () => {
    expect(appLinkRoute('https://asksiddha.app/m/today')).toBe('/m/today');
    expect(appLinkRoute('https://asksiddha.app/m/calendar/')).toBe('/m/calendar');
    expect(appLinkRoute('https://www.asksiddha.app/m/settings?utm=x')).toBe('/m/settings');
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
