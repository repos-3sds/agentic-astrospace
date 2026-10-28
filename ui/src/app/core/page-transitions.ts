import { inject } from '@angular/core';
import { Router, ViewTransitionInfo } from '@angular/router';
import { Capacitor } from '@capacitor/core';

/** How a navigation should move: deeper, back out, or across tabs. */
export type PageMotion = 'push' | 'pop' | 'tab';

const TAB_ROOTS = new Set(['/m/today', '/m/ask', '/m/calendar', '/m/explore', '/m/settings']);

function path(url: string): string {
  return url.split(/[?#]/)[0].replace(/\/+$/, '') || '/';
}

/**
 * Classifies a native-app navigation (N1). Tab to tab crossfades; Back (the
 * system gesture, the browser button, every `asBack` link) slides out;
 * anything else slides in. Navigations outside `/m/` get no motion: the web
 * app keeps its hard cuts.
 */
export function pageMotion(fromUrl: string, toUrl: string, trigger: string | undefined): PageMotion | null {
  const from = path(fromUrl);
  const to = path(toUrl);
  if (from === to || !from.startsWith('/m/') || !to.startsWith('/m/')) return null;
  if (TAB_ROOTS.has(from) && TAB_ROOTS.has(to)) return 'tab';
  return trigger === 'popstate' ? 'pop' : 'push';
}

function reducedMotion(): boolean {
  return typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
}

/**
 * `withViewTransitions` hook. Sets `data-nav` (push, pop, tab) and
 * `data-nav-os` (ios, android) on <html> for the CSS in styles-mobile.scss,
 * or skips the transition when it shouldn't animate. Runs in an injection
 * context. View Transitions need Android System WebView 111+ or iOS 18; on
 * older systems the router simply cuts, as before.
 */
export function onPageTransition(info: ViewTransitionInfo): void {
  const router = inject(Router);
  const navigation = router.getCurrentNavigation();
  const fromUrl = navigation?.previousNavigation?.finalUrl
    ? router.serializeUrl(navigation.previousNavigation.finalUrl)
    : router.url;
  const target = navigation?.finalUrl ?? navigation?.extractedUrl;
  const toUrl = target ? router.serializeUrl(target) : '';
  const motion = reducedMotion() ? null : pageMotion(fromUrl, toUrl, navigation?.trigger);
  const root = document.documentElement;
  // An iPhone edge swipe has already slid the screen off under the finger
  // (EdgeSwipeBackDirective); a second slide would replay it.
  if (!motion || root.dataset['swipeBack']) {
    info.transition.skipTransition();
    return;
  }
  root.dataset['nav'] = motion;
  root.dataset['navOs'] = Capacitor.getPlatform() === 'ios' ? 'ios' : 'android';
  const clear = () => { delete root.dataset['nav']; };
  info.transition.finished.then(clear, clear);
}
