import { Injectable, inject, signal } from '@angular/core';

import { ApiService } from './api.service';
import { apiUrl } from './api-origin';
import { AuthService } from './auth.service';
import { AskMessage, AskResponse, AskStreamEvent } from './models';

export const TOOL_LABELS: Record<string, string> = {
  get_birth_chart: 'Birth chart',
  get_varga_chart: 'Varga chart',
  get_today_panchanga: 'Panchanga',
  get_current_gochara: 'Gochara',
};

@Injectable({ providedIn: 'root' })
export class AskService {
  private api = inject(ApiService);
  private auth = inject(AuthService);

  /** per-kundli chat history, kept for the session */
  private histories = new Map<string, ReturnType<typeof signal<AskMessage[]>>>();

  readonly pending = signal(false);

  history(kundliId: string) {
    let h = this.histories.get(kundliId);
    if (!h) {
      h = signal<AskMessage[]>([]);
      this.histories.set(kundliId, h);
    }
    return h;
  }

  async ask(kundliId: string, question: string): Promise<void> {
    const history = this.history(kundliId);
    const priorTurns = history().map((m) => ({ role: m.role, content: m.content }));
    history.update((msgs) => [...msgs, { role: 'user', content: question }]);
    this.pending.set(true);
    try {
      const res = await this.api.post<AskResponse>(`/ask/${kundliId}`, {
        question,
        history: priorTurns,
      });
      history.update((msgs) => [
        ...msgs,
        { role: 'assistant', content: res.answer, tools: res.tools_used },
      ]);
    } catch (e) {
      history.update((msgs) => [
        ...msgs,
        { role: 'assistant', content: `Something went wrong: ${(e as Error).message}`, tools: [] },
      ]);
    } finally {
      this.pending.set(false);
    }
  }

  /**
   * Streamed counterpart to `ask()` — POST /ask/{kundliId}/stream
   * (ask_stream_routes.py). Raw `fetch` + `ReadableStream`, not `ApiService`
   * (HttpClient): `EventSource` can't carry a POST body, and this needs to
   * work unchanged inside the Capacitor WebView, not just a browser tab.
   */
  async *stream(
    kundliId: string,
    body: {
      question: string;
      thread_id?: string;
      start_thread?: boolean;
      language?: string;
      input_mode?: 'text' | 'voice';
    },
  ): AsyncGenerator<AskStreamEvent> {
    const token = await this.auth.getAccessToken();
    const response = await fetch(apiUrl(`/api/v1/ask/${encodeURIComponent(kundliId)}/stream`), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    });
    if (!response.ok || !response.body) {
      const text = await response.text().catch(() => '');
      const detail = (() => {
        try {
          return JSON.parse(text).detail as string;
        } catch {
          return text;
        }
      })();
      throw new Error(detail || `Ask stream failed (${response.status})`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let boundary = buffer.indexOf('\n\n');
      while (boundary !== -1) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const line = frame.split('\n').find((l) => l.startsWith('data: '));
        if (line) yield JSON.parse(line.slice('data: '.length)) as AskStreamEvent;
        boundary = buffer.indexOf('\n\n');
      }
    }
  }
}
