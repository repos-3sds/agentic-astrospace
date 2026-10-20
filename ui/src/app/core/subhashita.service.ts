import { Injectable, computed, inject, signal } from '@angular/core';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';

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
// Renamed from `daysFor` on 2026-10-20: caches filed under that key by build
// 550 may hold the shared rotation under the reader's name, so they are
// fetched again once.
const CACHE_OWNER_KEY = 'astrospace.subhashita.daysFrom';
const SEEN_KEY = 'astrospace.subhashita.seenOn';
const SHEET_OFF_KEY = 'astrospace.subhashita.sheetOff';
/** Fetched ahead, so the verse (and the home-screen widget) work offline for two weeks. */
const DAYS_AHEAD = 14;

/** YYYY-MM-DD for the reader's own calendar day, not UTC's. */
export function localIsoDate(date: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/**
 * Today's Subhashita: one verse a day from the Gita, Chanakya Niti and the
 * Puranas. Each account has its own rotation (Hawk, 2026-10-19), so the
 * cache remembers whose verses it holds and refetches for another account.
 *
 * Only today's verse is ever shown (Hawk, 2026-10-17: "no need to show
 * yesterdays"); the days ahead are cached so the verse opens without the
 * network and the widget has something to show tomorrow.
 */
@Injectable({ providedIn: 'root' })
export class SubhashitaService {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);

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
    const reader = this.auth.user()?.id ?? '';
    const cachedAhead = this.days().filter((d) => d.date >= today).length;
    // Verses cached before meanings existed (2026-10-18), or for another
    // account, are fetched again.
    if (this.today()?.meaning && cachedAhead >= DAYS_AHEAD / 2 && readCacheOwner() === reader) {
      return this.today();
    }
    try {
      const response = await this.api.get<{ items: Subhashita[]; reader?: string | null }>(
        `/subhashita?start=${today}&days=${DAYS_AHEAD}`,
      );
      this.days.set(response.items);
      // Filed under the rotation the server actually used. A run fetched
      // before the server knew per-account verses, or with a token it
      // rejected, is the shared one; filed under the reader it passed for
      // theirs and kept them on it for a week (2026-10-20, Hawk saw it).
      writeCache(response.items, response.reader ?? '');
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

  /** Whether the verse sheet opens on the day's first open (D8). On unless turned off. */
  readonly sheetOn = signal(readSheetOn());

  setSheetOn(on: boolean): void {
    this.sheetOn.set(on);
    try {
      if (on) localStorage.removeItem(SHEET_OFF_KEY);
      else localStorage.setItem(SHEET_OFF_KEY, '1');
    } catch { /* storage unavailable; holds for this visit */ }
  }
}

function readSheetOn(): boolean {
  try { return localStorage.getItem(SHEET_OFF_KEY) === null; } catch { return true; }
}

function readCache(): Subhashita[] {
  try {
    const rows = JSON.parse(localStorage.getItem(CACHE_KEY) ?? '[]');
    return Array.isArray(rows) ? rows : [];
  } catch {
    return [];
  }
}

/** The account the cached verses were fetched for; null before this was kept (shared verses). */
function readCacheOwner(): string | null {
  try { return localStorage.getItem(CACHE_OWNER_KEY); } catch { return null; }
}

function writeCache(rows: Subhashita[], reader: string): void {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(rows));
    localStorage.setItem(CACHE_OWNER_KEY, reader);
  } catch { /* storage unavailable */ }
}
