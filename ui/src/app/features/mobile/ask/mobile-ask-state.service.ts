import { Injectable } from '@angular/core';

import { AskResponse } from '../../../core/models';

/** Keeps the just-generated answer out of URLs while its thread is opened. */
@Injectable({ providedIn: 'root' })
export class MobileAskStateService {
  private readonly prefix = 'astrospace.ask.answer.';

  remember(response: AskResponse): void {
    if (response.thread_id) {
      sessionStorage.setItem(this.prefix + response.thread_id, response.answer);
    }
  }

  answer(threadId: string | null): string | null {
    return threadId ? sessionStorage.getItem(this.prefix + threadId) : null;
  }
}
