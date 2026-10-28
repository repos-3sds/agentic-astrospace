import { browserPlatform, openAppHref } from './open-app';

describe('open the app from a browser page', () => {
  const nav = (userAgent: string, maxTouchPoints = 0) => ({ userAgent, maxTouchPoints });

  it('tells iPhone, iPad, Android and desktop apart', () => {
    expect(browserPlatform(nav('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)'))).toBe('ios');
    // iPadOS asks for desktop sites and reports itself as a Mac with touch.
    expect(browserPlatform(nav('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 5))).toBe('ios');
    expect(browserPlatform(nav('Mozilla/5.0 (Linux; Android 15; SM-S938B)'))).toBe('android');
    expect(browserPlatform(nav('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'))).toBe('desktop');
  });

  it('opens the app on Android with the Play listing as the fallback', () => {
    const href = openAppHref('android');
    expect(href).toMatch(/^intent:\/\/auth\/callback#Intent;scheme=app\.asksiddha\.mobile;package=app\.asksiddha\.mobile;/);
    expect(decodeURIComponent(href)).toContain('play.google.com/store/apps/details?id=app.asksiddha.mobile');
  });

  it('never points a reader at the Cloud Run address', () => {
    for (const p of ['ios', 'android', 'desktop'] as const) expect(openAppHref(p)).not.toContain('run.app');
  });
});
