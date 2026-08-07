import { Injectable } from '@angular/core';

import { AskResponse } from '../../../core/models';
import { MobileAskThread } from './mobile-ask-thread.service';

/** Keeps the just-generated answer out of URLs while its thread is opened. */
@Injectable({ providedIn: 'root' })
export class MobileAskStateService {
  private readonly prefix = 'astrospace.ask.answer.';
  private readonly threadsPrefix = 'astrospace.ask.recentThreads.';

  remember(response: AskResponse): void {
    if (response.thread_id) {
      this.rememberAnswer(response.thread_id, response.answer);
    }
  }

  rememberAnswer(threadId: string, answer: string): void {
    sessionStorage.setItem(this.prefix + threadId, answer);
  }

  answer(threadId: string | null): string | null {
    return threadId ? sessionStorage.getItem(this.prefix + threadId) : null;
  }

  rememberThread(thread: MobileAskThread): void {
    const key = this.threadsPrefix + thread.kundli_id;
    const existing = this.recentThreads(thread.kundli_id)
      .filter((item) => item.id !== thread.id);
    sessionStorage.setItem(key, JSON.stringify([thread, ...existing].slice(0, 20)));
  }

  recentThreads(kundliId: string): MobileAskThread[] {
    const raw = sessionStorage.getItem(this.threadsPrefix + kundliId);
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw) as MobileAskThread[];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }
}
