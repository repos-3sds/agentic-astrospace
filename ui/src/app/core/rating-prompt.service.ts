import { Injectable } from '@angular/core';
import { Capacitor, registerPlugin } from '@capacitor/core';

interface InAppReviewPlugin {
  request(): Promise<{ asked: boolean }>;
}

const InAppReview = registerPlugin<InAppReviewPlugin>('InAppReview');

const STORAGE_KEY = 'siddha.rating-prompt';
/** Different days the app was opened before Play's card may be asked for. */
export const MIN_ACTIVE_DAYS = 5;
/** Answers received or briefs listened to the end. */
export const MIN_GOOD_MOMENTS = 3;
/** Play rations the card itself; this keeps the app from asking more often. */
export const ASK_AGAIN_AFTER_DAYS = 120;
const DAY_MS = 86_400_000;

interface RatingState {
  days: string[];
  moments: number;
  askedAt: number | null;
}

/**
 * When to ask Play for its rating card (audit N23; InAppReviewPlugin on
 * Android). Never in the middle of something: a good moment (an Ask answer,
 * a brief heard to the end) is only counted, and the card is asked for on a
 * later app open, a few seconds after the shell settles. Only on the native
 * Android app; iOS waits for its own build.
 */
@Injectable({ providedIn: 'root' })
export class RatingPromptService {
  /** Count one good moment. */
  goodMoment(): void {
    const state = this.read();
    state.moments += 1;
    this.write(state);
  }

  /** Note today's open, and ask Play for the card if the reader qualifies. */
  async onAppOpen(now = new Date()): Promise<boolean> {
    if (Capacitor.getPlatform() !== 'android') return false;
    const state = this.read();
    const today = now.toISOString().slice(0, 10);
    if (!state.days.includes(today)) state.days = [...state.days, today].slice(-30);
    const due = shouldAsk(state, now.getTime());
    if (due) state.askedAt = now.getTime();
    this.write(state);
    if (!due) return false;
    try {
      return (await InAppReview.request()).asked;
    } catch {
      return false;
    }
  }

  private read(): RatingState {
    try {
      const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null') as Partial<RatingState> | null;
      return {
        days: Array.isArray(raw?.days) ? raw.days : [],
        moments: typeof raw?.moments === 'number' ? raw.moments : 0,
        askedAt: typeof raw?.askedAt === 'number' ? raw.askedAt : null,
      };
    } catch {
      return { days: [], moments: 0, askedAt: null };
    }
  }

  private write(state: RatingState): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      /* private mode or storage full: the reader is simply asked later */
    }
  }
}

export function shouldAsk(state: RatingState, nowMs: number): boolean {
  if (state.days.length < MIN_ACTIVE_DAYS || state.moments < MIN_GOOD_MOMENTS) return false;
  return state.askedAt === null || nowMs - state.askedAt >= ASK_AGAIN_AFTER_DAYS * DAY_MS;
}
