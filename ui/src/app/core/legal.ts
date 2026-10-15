import { Browser } from '@capacitor/browser';
import { Capacitor } from '@capacitor/core';
import { apiUrl } from './api-origin';

export type LegalDocument = 'terms' | 'privacy';

/**
 * Terms and the Privacy Policy are served by the API (astrospace/api/legal_routes.py)
 * so one URL works in the store listing, in a browser and inside the app.
 * On the web the SPA shares the API origin, so the path is relative; a native
 * build must use the absolute API origin or the WebView resolves it against
 * the bundle and 404s.
 */
export function legalUrl(doc: LegalDocument): string {
  return apiUrl(`/legal/${doc}`);
}

/**
 * Open a legal page. Native: the system browser (a WebView page with no app
 * chrome is a dead end for the reader). Web: a new tab, so the sign-in form
 * they were filling in is still there when they come back.
 */
export async function openLegal(doc: LegalDocument, event?: Event): Promise<void> {
  event?.preventDefault();
  const url = legalUrl(doc);
  if (Capacitor.isNativePlatform()) {
    await Browser.open({ url });
  } else {
    window.open(url, '_blank', 'noopener');
  }
}
