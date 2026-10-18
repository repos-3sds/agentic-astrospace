import { Injectable, computed, inject, signal } from '@angular/core';
import { ApiService } from './api.service';

/** One verse, as /api/v1/subhashita returns it (astrospace/core/subhashita). */
export interface Subhashita {
  date: string;
  id: string;
  source: string;
  ref: string;
  sanskrit: string;
  english: string;
  /** One plain line on what the verse asks of the reader. */
  meaning: string;
}

export const SUBHASHITA_TITLE = 'Today’s Subhashita';

const CACHE_KEY = 'astrospace.subhashita.days';
const SEEN_KEY = 'astrospace.subhashita.seenOn';
/** Fetched ahead, so the verse (and the home-screen widget) work offline for two weeks. */
const DAYS_AHEAD = 14;

/** YYYY-MM-DD for the reader's own calendar day, not UTC's. */
export function localIsoDate(date: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/**
 * Today's Subhashita: one verse a day from the Gita, Chanakya Niti and the
 * Puranas, the same for every reader on a date.
 *
 * Only today's verse is ever shown (Hawk, 2026-10-17: "no need to show
 * yesterdays"); the days ahead are cached so the verse opens without the
 * network and the widget has something to show tomorrow.
 */
@Injectable({ providedIn: 'root' })
export class SubhashitaService {
  private readonly api = inject(ApiService);

  private readonly days = signal<Subhashita[]>(readCache());
  private readonly date = signal(localIsoDate());
  readonly error = signal<string | null>(null);

  readonly today = computed(() => this.days().find((d) => d.date === this.date()) ?? null);
  /** Today and the cached days after it, for the widget snapshot. */
  readonly upcoming = computed(() => this.days().filter((d) => d.date >= this.date()));

  /** Loads today's verse, from the cache when it holds today and the run ahead. */
  async load(): Promise<Subhashita | null> {
    const today = localIsoDate();
    this.date.set(today);
    const cachedAhead = this.days().filter((d) => d.date >= today).length;
    // Verses cached before meanings existed (2026-10-18) are fetched again.
    if (this.today()?.meaning && cachedAhead >= DAYS_AHEAD / 2) return this.today();
    try {
      const response = await this.api.get<{ items: Subhashita[] }>(
        `/subhashita?start=${today}&days=${DAYS_AHEAD}`,
      );
      this.days.set(response.items);
      writeCache(response.items);
      this.error.set(null);
    } catch (err) {
      this.error.set(err instanceof Error ? err.message : String(err));
    }
    return this.today();
  }

  /** Whether today's verse has not yet been shown on opening the app. */
  unseenToday(): boolean {
    try {
      return localStorage.getItem(SEEN_KEY) !== localIsoDate();
    } catch {
      return false;
    }
  }

  /** No verse has ever been offered on this device: a reader on their first day. */
  neverOffered(): boolean {
    try {
      return localStorage.getItem(SEEN_KEY) === null;
    } catch {
      return false;
    }
  }

  markSeen(): void {
    try { localStorage.setItem(SEEN_KEY, localIsoDate()); } catch { /* storage unavailable */ }
  }
}

function readCache(): Subhashita[] {
  try {
    const rows = JSON.parse(localStorage.getItem(CACHE_KEY) ?? '[]');
    return Array.isArray(rows) ? rows : [];
  } catch {
    return [];
  }
}

function writeCache(rows: Subhashita[]): void {
  try { localStorage.setItem(CACHE_KEY, JSON.stringify(rows)); } catch { /* storage unavailable */ }
}
