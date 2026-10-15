import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { AuthService } from './auth.service';
import { apiUrl } from './api-origin';
import { ConnectivityService } from './connectivity.service';

// Relative on web (the SPA is served same-origin by FastAPI); absolute in a
// Capacitor WebView, where a relative path resolves inside the app bundle.
const BASE = () => apiUrl('/api/v1');

/**
 * A structured refusal: the product declines to answer by design (health,
 * legal and money intents), so the screen shows a refer-out card and no retry.
 */
export class ReferOutError extends Error {
  override readonly name = 'ReferOutError';
  constructor(message: string, readonly domain: string | null = null) {
    super(message);
  }
}

/**
 * An HTTP failure with a sentence meant for the screen. `message` is the
 * friendly copy; `detail` keeps the backend's raw `detail` (a string, or the
 * JSON of a validation array) for practitioner diagnostics and logs. Until
 * 2026-10-15 the raw detail *was* the message, so "Internal Server Error",
 * "City 'Mumbaii' not in offline database." and Pydantic JSON reached the
 * generic error card verbatim.
 */
export class ApiError extends Error {
  override readonly name = 'ApiError';
  constructor(message: string, readonly status: number, readonly detail: string) {
    super(message);
  }
}

const NETWORK_MESSAGE = 'We couldn’t reach the guidance service — check your connection and try again.';

export function friendlyApiMessage(status: number, detail: unknown): string {
  const raw = typeof detail === 'string' ? detail : '';
  if (status === 0) return NETWORK_MESSAGE;
  if (status === 401 || status === 403) return 'Please sign in again to continue.';
  if (status === 404) return 'We couldn’t find what this screen needs. The profile may have been removed — pick another or try again.';
  if (status === 409) {
    return /\b(self|yourself)\b/i.test(raw)
      ? 'You already have a profile for yourself. Edit it from Settings › Profiles instead of adding another.'
      : 'That already exists, so nothing was added.';
  }
  if (status === 408 || status === 504) return 'That took too long to answer. Try again in a moment.';
  if (status === 429) return 'Too many requests right now. Wait a moment and try again.';
  if (status >= 500) return 'The guidance service hit a problem on our side. Try again in a moment.';
  // The kundli API refuses an unresolvable birth place with a sentence
  // written for the person ("We couldn’t find “Mumbaii” in IN. Choose the
  // birth place from the search results."); it is shown as-is.
  if (status === 422 && /birth place from the search results/i.test(raw)) return raw;
  if (status === 422 || Array.isArray(detail)) return 'Some of the details sent weren’t valid. Check the date, time and place and try again.';
  if (/\bcity\b/i.test(raw)) return 'We couldn’t place that city. Check the place of birth and try again.';
  if (/timezone/i.test(raw)) return 'We couldn’t work out the time zone for that place. Check the place of birth and try again.';
  if (/birth details/i.test(raw)) return 'The saved birth details could not be used. Check the date, time and place of birth.';
  if (/must be YYYY-MM-DD|date must be/i.test(raw)) return 'That date couldn’t be read. Pick the date again.';
  return 'That request couldn’t be completed. Check the details and try again.';
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private connectivity = inject(ConnectivityService);

  async get<T>(path: string): Promise<T> {
    return this.unwrap(firstValueFrom(this.http.get<T>(BASE() + path, await this.options())));
  }

  async post<T>(path: string, body: unknown, headers?: Record<string, string>): Promise<T> {
    return this.unwrap(firstValueFrom(this.http.post<T>(BASE() + path, body, await this.options(headers))));
  }

  async put<T>(path: string, body: unknown): Promise<T> {
    return this.unwrap(firstValueFrom(this.http.put<T>(BASE() + path, body, await this.options())));
  }

  async patch<T>(path: string, body: unknown, headers?: Record<string, string>): Promise<T> {
    return this.unwrap(firstValueFrom(this.http.patch<T>(BASE() + path, body, await this.options(headers))));
  }

  async delete(path: string): Promise<void> {
    return this.unwrap(firstValueFrom(this.http.delete<void>(BASE() + path, await this.options())));
  }

  async deleteWithBody<T>(path: string, body: unknown, headers?: Record<string, string>): Promise<T> {
    return this.unwrap(firstValueFrom(this.http.delete<T>(BASE() + path, {
      ...(await this.options(headers)),
      body,
    })));
  }

  private async options(extraHeaders?: Record<string, string>): Promise<{ headers?: Record<string, string> }> {
    const token = await this.auth.getAccessToken();
    const headers = {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(extraHeaders ?? {}),
    };
    return Object.keys(headers).length ? { headers } : {};
  }

  private async unwrap<T>(req: Promise<T>): Promise<T> {
    try {
      const value = await req;
      this.connectivity.noteRequestSuccess();
      return value;
    } catch (e) {
      this.connectivity.noteRequestFailure(e);
      if (e instanceof HttpErrorResponse) {
        const detail = (e.error && (e.error.detail || e.error.message)) || e.statusText;
        // Structured refusals (`{kind: "refer_out", message}` from readings and
        // muhurta) carry a sentence meant for the screen; show that, not JSON.
        if (detail && typeof detail === 'object' && typeof detail.message === 'string') {
          throw detail.kind === 'refer_out'
            ? new ReferOutError(detail.message, detail.domain)
            : new Error(detail.message);
        }
        const raw = typeof detail === 'string' ? detail : JSON.stringify(detail ?? null);
        throw new ApiError(friendlyApiMessage(e.status, detail), e.status, raw);
      }
      throw e;
    }
  }
}
