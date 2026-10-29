import { DestroyRef, Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { App as CapacitorApp, URLOpenListenerEvent } from '@capacitor/app';
import { Capacitor } from '@capacitor/core';
import { noteDeepLink } from './deep-link-arrival';

/** The website hosts whose /m/ links the app claims (AndroidManifest.xml). */
const APP_LINK_HOSTS = new Set(['asksiddha.app', 'www.asksiddha.app']);

/**
 * Screens an email or web link may open. Any page on the web can link to
 * asksiddha.app, so this is an allowlist, as for widgets (D15): screens
 * only, nothing that acts on arrival, and no query string except a date on
 * Calendar's day view. Every path an email button uses must be here, or the
 * phone opens Siddha and goes nowhere (sweep 2026-10-29 F-4);
 * tests/test_email_app_links.py checks that.
 */
export const APP_LINK_ROUTES = new Set([
  '/m/today', '/m/ask', '/m/calendar', '/m/calendar/day', '/m/explore', '/m/settings',
  '/m/settings/notifications', '/m/notifications', '/m/remedies', '/m/subhashita', '/m/readings',
  '/m/chart', '/m/chart/periods', '/m/chart/yogas', '/m/compat',
]);

/** The one query an app link may carry: which day Calendar opens on. */
const DATED_ROUTES = new Set(['/m/calendar/day']);
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

/** The in-app route for an https://asksiddha.app/m/… link, or null. */
export function appLinkRoute(url: string | null | undefined): string | null {
  if (!url) return null;
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return null;
  }
  if (parsed.protocol !== 'https:' || !APP_LINK_HOSTS.has(parsed.hostname)) return null;
  const path = parsed.pathname.replace(/\/+$/, '');
  if (!APP_LINK_ROUTES.has(path)) return null;
  const date = parsed.searchParams.get('date');
  return DATED_ROUTES.has(path) && date && ISO_DATE.test(date) ? `${path}?date=${date}` : path;
}

let launchHandled = false;

/**
 * Email buttons link to https://asksiddha.app/m/today and the like. With
 * verified App Links those open the app instead of the landing page
 * (nativeness audit N17); this routes them inside it.
 */
@Injectable({ providedIn: 'root' })
export class AppLinksService {
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private started = false;

  start(): void {
    if (this.started || !Capacitor.isNativePlatform()) return;
    this.started = true;
    const listener = CapacitorApp.addListener('appUrlOpen', (event: URLOpenListenerEvent) => this.open(event.url));
    this.destroyRef.onDestroy(() => void listener.then((l) => l.remove()));
    if (!launchHandled) {
      launchHandled = true;
      void CapacitorApp.getLaunchUrl().then((launch) => this.open(launch?.url)).catch(() => undefined);
    }
  }

  private open(url: string | undefined): void {
    const route = appLinkRoute(url);
    if (!route) return;
    noteDeepLink();
    void this.router.navigateByUrl(route);
  }
}
