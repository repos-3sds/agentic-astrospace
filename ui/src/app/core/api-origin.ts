import { Capacitor } from '@capacitor/core';

/**
 * Where the API lives, as seen from wherever this bundle is running.
 *
 * On the web the SPA is served by FastAPI itself, so the API shares the page's
 * origin and a relative base is not just fine but correct — it follows the
 * deployment automatically, whatever host it lands on.
 *
 * A Capacitor WebView is different in a way that breaks silently. The bundle is
 * served from `capacitor://localhost` (Android) or `ionic://localhost` (iOS),
 * so `/api/v1/...` resolves against the *bundle*, not the server: every request
 * 404s inside the app with nothing in the network log to explain it. Native
 * builds therefore need an absolute origin.
 *
 * That origin is a public deployment URL, not a secret, so it is configured
 * rather than injected — see `environment.ts`.
 */
import { environment } from '../../environments/environment';

export function apiOrigin(): string {
  if (!Capacitor.isNativePlatform()) {
    // Relative — same-origin, unchanged web behaviour.
    return '';
  }
  const origin = environment.nativeApiOrigin?.replace(/\/+$/, '');
  if (!origin) {
    throw new Error(
      'nativeApiOrigin is not configured. A native build cannot use a ' +
        'relative API path, because it would resolve inside the app bundle.',
    );
  }
  return origin;
}

/** Absolute or relative URL for an API path such as `/api/v1/kundlis`. */
export function apiUrl(path: string): string {
  return apiOrigin() + path;
}
