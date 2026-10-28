import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { TimeoutError, catchError, retry, throwError, timeout, timer } from 'rxjs';

/** How long an API read may go without an answer before it counts as failed. */
export const API_GET_TIMEOUT_MS = 8_000;
/**
 * Reads that legitimately take longer than API_GET_TIMEOUT_MS. The daily
 * brief is normally already written and answers at once, but when the
 * schedule has not reached a profile the server writes it during the request
 * (two model calls at most, 60 s each); cut off at 8 s, that request could
 * never succeed and Today kept the template. A couple's "About you two"
 * section is written the same way the first time a pair is opened.
 */
export const API_SLOW_GET_TIMEOUT_MS = 130_000;
const SLOW_READS = [/\/daily\/brief(\?|$)/, /\/compatibility\/[^/?]+\/insight(\?|$)/];
/**
 * Reads that compute a span of days. Each is a few seconds of ephemeris work,
 * more on a cold server, so 8 s cut them off before they could answer and the
 * retry started the work again: Muhurta never returned, and a month of
 * festivals or the calendar failed until Retry found the server warm.
 */
export const API_COMPUTE_GET_TIMEOUT_MS = 45_000;
/**
 * A profile's day and natal chart are the first thing a profile switch asks
 * for, and when the API has scaled to zero the answer waits for the server to
 * start (10-20 s). At 8 s the read was cut off, retried from scratch, cut off
 * again, and Today showed "Unable to load this view" for a profile that was
 * fine (2026-10-28). The work itself is well under a second once up.
 */
const COMPUTE_READS = [
  /\/calendar-intelligence(\?|$)/,
  /\/muhurta\/(?!goals)[^/?]+(\?|$)/,
  /\/festivals\/(upcoming|year)/,
  /\/context\/[^/?]+\/daily(\?|$)/,
  /\/vedic\/[^/?]+\/all(\?|$)/,
];

export function readTimeoutMs(req: HttpRequest<unknown>): number {
  if (SLOW_READS.some((pattern) => pattern.test(req.url))) return API_SLOW_GET_TIMEOUT_MS;
  if (COMPUTE_READS.some((pattern) => pattern.test(req.url))) return API_COMPUTE_GET_TIMEOUT_MS;
  return API_GET_TIMEOUT_MS;
}

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
    timeout({ each: readTimeoutMs(req) }),
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
