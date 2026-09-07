import { HttpErrorResponse } from '@angular/common/http';
import { computed, Injectable, signal } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import { Network } from '@capacitor/network';

import { apiUrl } from './api-origin';

export type ConnectivityState = 'online' | 'reconnecting' | 'offline';

export function isReachabilityFailure(error: unknown): boolean {
  if (error instanceof HttpErrorResponse) return error.status === 0;
  if (error instanceof TypeError) return true;
  const message = error instanceof Error ? error.message : String(error ?? '');
  return /failed to fetch|network request failed|load failed|networkerror/i.test(message);
}

@Injectable({ providedIn: 'root' })
export class ConnectivityService {
  readonly state = signal<ConnectivityState>(
    typeof navigator !== 'undefined' && navigator.onLine === false ? 'offline' : 'online',
  );
  readonly offline = computed(() => this.state() === 'offline');
  readonly reconnecting = computed(() => this.state() === 'reconnecting');

  private probeId = 0;

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('offline', () => this.markOffline());
      window.addEventListener('online', () => void this.retry());
    }
    if (Capacitor.isNativePlatform()) void this.installNativeListener();
  }

  noteRequestSuccess(): void {
    this.state.set('online');
  }

  noteRequestFailure(error: unknown): void {
    if (isReachabilityFailure(error)) this.markOffline();
    else this.noteRequestSuccess();
  }

  async retry(): Promise<boolean> {
    const request = ++this.probeId;
    this.state.set('reconnecting');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5_000);
    try {
      const response = await fetch(apiUrl('/api/health'), {
        cache: 'no-store',
        signal: controller.signal,
      });
      if (request !== this.probeId) return this.state() === 'online';
      // Any HTTP response proves reachability. Endpoint-level failures remain
      // the responsibility of the screen that made the request.
      this.state.set('online');
      return response.ok;
    } catch {
      if (request === this.probeId) this.markOffline();
      return false;
    } finally {
      clearTimeout(timeout);
    }
  }

  private markOffline(): void {
    this.probeId += 1;
    this.state.set('offline');
  }

  private async installNativeListener(): Promise<void> {
    const initial = await Network.getStatus().catch(() => null);
    if (initial && !initial.connected) this.markOffline();
    await Network.addListener('networkStatusChange', (status) => {
      if (!status.connected) this.markOffline();
      else void this.retry();
    });
  }
}
