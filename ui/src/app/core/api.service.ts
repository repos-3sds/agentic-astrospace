import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { AuthService } from './auth.service';
import { apiUrl } from './api-origin';
import { ConnectivityService } from './connectivity.service';

// Relative on web (the SPA is served same-origin by FastAPI); absolute in a
// Capacitor WebView, where a relative path resolves inside the app bundle.
const BASE = () => apiUrl('/api/v1');

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
        throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
      }
      throw e;
    }
  }
}
