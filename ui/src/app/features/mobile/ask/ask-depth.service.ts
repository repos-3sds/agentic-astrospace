import { Injectable, signal } from '@angular/core';

export type AskDepth = 'fast' | 'deep';

const STORAGE_KEY = 'siddha.ask.depth';

/**
 * Fast or Deep for the next question (Hawk, 2026-10-28: "like Claude's
 * thinking mode"). Fast is today's Ask, about 25 s. Deep reads the chart from
 * every side and shows how it weighed it, about a minute. Both cost one
 * question, for every reader. Remembered on this device, Fast by default.
 */
@Injectable({ providedIn: 'root' })
export class AskDepthService {
  readonly depth = signal<AskDepth>(this.read());

  toggle(): void {
    this.set(this.depth() === 'deep' ? 'fast' : 'deep');
  }

  set(depth: AskDepth): void {
    this.depth.set(depth);
    try {
      localStorage.setItem(STORAGE_KEY, depth);
    } catch {
      // Private mode or blocked storage: the choice lasts for this session.
    }
  }

  private read(): AskDepth {
    try {
      return localStorage.getItem(STORAGE_KEY) === 'deep' ? 'deep' : 'fast';
    } catch {
      return 'fast';
    }
  }
}
