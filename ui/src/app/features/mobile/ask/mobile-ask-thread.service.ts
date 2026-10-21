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

/** Why a reader reported an answer; the server keeps the same five. */
export type AnswerReportReason = 'wrong' | 'harmful' | 'offensive' | 'advice' | 'other';

/** "Report this answer" (Google Play's rule for AI-generated content). The
 * answer and question are sent as the reader saw them, so the report stays
 * readable after the conversation is deleted. */
export interface AnswerReport {
  reason: AnswerReportReason;
  note?: string | null;
  answer: string;
  question?: string | null;
  thread_id?: string | null;
  message_id?: string | null;
  experience_mode?: 'guided' | 'balanced' | 'practitioner';
  language?: 'en' | 'te';
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

  async report(report: AnswerReport): Promise<void> {
    await this.api.post('/ask/reports', report);
  }

  async delete(threadId: string): Promise<void> {
    await this.api.delete(`/ask/threads/${encodeURIComponent(threadId)}`);
  }
}
