import { Capacitor } from '@capacitor/core';

/**
 * "Open Siddha" from a browser page of the web app. The public site does the
 * same in firebase-public/js/open-app.js; keep the two in step.
 *
 * Android goes through an intent: URL, so Chrome falls back to the Play
 * listing by itself when the app is missing. iOS has no fallback, so if the
 * page is still showing a moment later we go to asksiddha.app/open, which
 * says how to get the app.
 */
export type BrowserPlatform = 'ios' | 'android' | 'desktop';

export const OPEN_PAGE = 'https://asksiddha.app/open';
const SCHEME_LINK = 'app.asksiddha.mobile://auth/callback';
const ANDROID_LINK =
  'intent://auth/callback#Intent;scheme=app.asksiddha.mobile;package=app.asksiddha.mobile;' +
  'S.browser_fallback_url=' +
  encodeURIComponent('https://play.google.com/store/apps/details?id=app.asksiddha.mobile') +
  ';end';

export function browserPlatform(nav: Pick<Navigator, 'userAgent' | 'maxTouchPoints'> = navigator): BrowserPlatform {
  const ua = nav.userAgent || '';
  if (/iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && nav.maxTouchPoints > 1)) return 'ios';
  if (/Android/.test(ua)) return 'android';
  return 'desktop';
}

/** Where the "Open app" link points before any script runs. */
export function openAppHref(platform: BrowserPlatform): string {
  return platform === 'android' ? ANDROID_LINK : OPEN_PAGE;
}

/** Click handler for an "Open app" link; leaves desktop clicks to the href. */
export function openSiddhaApp(event: Event, platform: BrowserPlatform = browserPlatform()): void {
  if (Capacitor.isNativePlatform() || platform !== 'ios') return;
  event.preventDefault();
  let left = false;
  const onHide = () => { if (document.hidden) left = true; };
  document.addEventListener('visibilitychange', onHide);
  window.location.href = SCHEME_LINK;
  setTimeout(() => {
    document.removeEventListener('visibilitychange', onHide);
    if (!left && !document.hidden) window.location.href = OPEN_PAGE;
  }, 1600);
}
