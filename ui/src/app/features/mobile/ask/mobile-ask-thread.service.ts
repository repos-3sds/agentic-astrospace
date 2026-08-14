import { Injectable, inject } from '@angular/core';

import { ApiService } from '../../../core/api.service';

export interface MobileAskThread {
  id: string;
  kundli_id: string;
  title: string;
  message_count: number;
  last_message_at: string | null;
  archived_at?: string | null;
  created_at: string | null;
}

export interface MobileAskMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  domain: string | null;
  refer_out_kind: string | null;
  evidence: Record<string, unknown> | null;
  created_at: string | null;
}

export interface MobileAskThreadDetail {
  thread: MobileAskThread;
  messages: MobileAskMessage[];
}

@Injectable({ providedIn: 'root' })
export class MobileAskThreadService {
  private readonly api = inject(ApiService);

  async list(kundliId: string, archived = false): Promise<MobileAskThread[]> {
    const result = await this.api.get<{ threads: MobileAskThread[] }>(
      `/ask/threads?kundli_id=${encodeURIComponent(kundliId)}&archived=${archived}`,
    );
    return result.threads;
  }

  get(threadId: string): Promise<MobileAskThreadDetail> {
    return this.api.get<MobileAskThreadDetail>(
      `/ask/threads/${encodeURIComponent(threadId)}`,
    );
  }

  async archive(threadId: string): Promise<void> {
    await this.api.post(`/ask/threads/${encodeURIComponent(threadId)}/archive`, {});
  }

  async restore(threadId: string): Promise<void> {
    await this.api.post(`/ask/threads/${encodeURIComponent(threadId)}/restore`, {});
  }

  async delete(threadId: string): Promise<void> {
    await this.api.delete(`/ask/threads/${encodeURIComponent(threadId)}`);
  }
}
