import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { TimeoutError, catchError, retry, throwError, timeout, timer } from 'rxjs';

/** How long an API read may go without an answer before it counts as failed. */
export const API_GET_TIMEOUT_MS = 8_000;
/** Pause before the single retry, long enough for a flapping radio to settle. */
export const API_GET_RETRY_DELAY_MS = 400;

const RETRYABLE_STATUS = new Set([0, 408, 502, 503, 504]);

/**
 * Bounds and retries idempotent API reads.
 *
 * Until 2026-10-15 no request had a timeout, so on a weak signal a screen
 * (and at boot, the splash) waited on the OS's own socket timeout, which can
 * be minutes. A GET under /api now fails after API_GET_TIMEOUT_MS without a
 * response and is retried once on a timeout, a network failure or a gateway
 * error. Only GETs: retrying a POST could create a second kundli or charge a
 * second Ask. Streams and downloads are left alone, since a long answer is
 * not a stalled one.
 */
export const httpResilienceInterceptor: HttpInterceptorFn = (req, next) => {
  if (!isBoundedRead(req)) return next(req);
  return next(req).pipe(
    // `each`, not `first`: the fetch backend emits a Sent event immediately,
    // so the clock that matters is the gap until the response arrives.
    timeout({ each: API_GET_TIMEOUT_MS }),
    catchError((error: unknown) =>
      throwError(() =>
        error instanceof TimeoutError
          ? new HttpErrorResponse({
              status: 408,
              statusText: 'Request timed out',
              url: req.urlWithParams,
              error: { detail: 'Request timed out' },
            })
          : error,
      ),
    ),
    retry({
      count: 1,
      delay: (error: unknown) =>
        shouldRetry(error) ? timer(API_GET_RETRY_DELAY_MS) : throwError(() => error),
    }),
  );
};

export function isBoundedRead(req: HttpRequest<unknown>): boolean {
  if (req.method !== 'GET') return false;
  // Relative on the web, absolute in the native WebView (see api-origin.ts).
  if (!/^(?:[a-z][a-z0-9+.-]*:\/\/[^/]+)?\/api\//i.test(req.url)) return false;
  if (req.reportProgress) return false;
  if (req.responseType === 'blob' || req.responseType === 'arraybuffer') return false;
  const accept = req.headers.get('Accept') ?? '';
  if (accept.includes('text/event-stream')) return false;
  if (/\/stream(\?|$)/.test(req.url)) return false;
  return true;
}

function shouldRetry(error: unknown): boolean {
  if (!(error instanceof HttpErrorResponse)) return false;
  if (!RETRYABLE_STATUS.has(error.status)) return false;
  // Known offline: a second attempt cannot succeed and only delays the
  // cached fallback. The connectivity service retries when the radio returns.
  if (error.status === 0 && typeof navigator !== 'undefined' && navigator.onLine === false) return false;
  return true;
}
