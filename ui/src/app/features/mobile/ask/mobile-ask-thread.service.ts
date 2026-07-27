import { Injectable, inject } from '@angular/core';

import { ApiService } from '../../../core/api.service';
import { AskResponse } from '../../../core/models';

export interface MobileAskThread {
  id: string;
  kundli_id: string;
  title: string;
  message_count: number;
  last_message_at: string | null;
  created_at: string | null;
}

export interface MobileAskMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  domain: string | null;
  refer_out_kind: string | null;
  created_at: string | null;
}

export interface MobileAskThreadDetail {
  thread: MobileAskThread;
  messages: MobileAskMessage[];
}

@Injectable({ providedIn: 'root' })
export class MobileAskThreadService {
  private readonly api = inject(ApiService);

  async list(kundliId: string): Promise<MobileAskThread[]> {
    const result = await this.api.get<{ threads: MobileAskThread[] }>(
      `/ask/threads?kundli_id=${encodeURIComponent(kundliId)}`,
    );
    return result.threads;
  }

  get(threadId: string): Promise<MobileAskThreadDetail> {
    return this.api.get<MobileAskThreadDetail>(
      `/ask/threads/${encodeURIComponent(threadId)}`,
    );
  }

  continue(kundliId: string, threadId: string, question: string): Promise<AskResponse> {
    return this.api.post<AskResponse>(`/ask/${encodeURIComponent(kundliId)}`, {
      question,
      thread_id: threadId,
      input_mode: 'text',
    });
  }

  async archive(threadId: string): Promise<void> {
    await this.api.post(`/ask/threads/${encodeURIComponent(threadId)}/archive`, {});
  }
}
