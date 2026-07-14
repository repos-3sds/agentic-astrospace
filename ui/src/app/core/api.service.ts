import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { AuthService } from './auth.service';

const BASE = '/api/v1';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);

  async get<T>(path: string): Promise<T> {
    return this.unwrap(firstValueFrom(this.http.get<T>(BASE + path, await this.options())));
  }

  async post<T>(path: string, body: unknown): Promise<T> {
    return this.unwrap(firstValueFrom(this.http.post<T>(BASE + path, body, await this.options())));
  }

  async put<T>(path: string, body: unknown): Promise<T> {
    return this.unwrap(firstValueFrom(this.http.put<T>(BASE + path, body, await this.options())));
  }

  async patch<T>(path: string, body: unknown): Promise<T> {
    return this.unwrap(firstValueFrom(this.http.patch<T>(BASE + path, body, await this.options())));
  }

  async delete(path: string): Promise<void> {
    return this.unwrap(firstValueFrom(this.http.delete<void>(BASE + path, await this.options())));
  }

  private async options(): Promise<{ headers?: Record<string, string> }> {
    const token = await this.auth.getAccessToken();
    return token ? { headers: { Authorization: `Bearer ${token}` } } : {};
  }

  private async unwrap<T>(req: Promise<T>): Promise<T> {
    try {
      return await req;
    } catch (e) {
      if (e instanceof HttpErrorResponse) {
        const detail = (e.error && (e.error.detail || e.error.message)) || e.statusText;
        throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
      }
      throw e;
    }
  }
}
