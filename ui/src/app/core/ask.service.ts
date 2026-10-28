import { Injectable, inject, signal } from '@angular/core';
import { EntitlementLimitError, isEntitlementDenial } from './entitlement-denial';

import { ApiService } from './api.service';
import { apiUrl } from './api-origin';
import { AuthService } from './auth.service';
import { AskMessage, AskResponse, AskStreamEvent, AskSuggestionsPayload } from './models';
import { PreferencesService } from './preferences.service';

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
  private preferences = inject(PreferencesService);

  /** per-kundli chat history, kept for the session */
  private histories = new Map<string, ReturnType<typeof signal<AskMessage[]>>>();
  /** per-kundli server thread: the server replays its own stored turns, so a
   * client can't hand the model a forged earlier answer (S15). */
  private threads = new Map<string, string>();

  readonly pending = signal(false);

  /** Ask home suggestions, per profile, mode and day: they follow the running
   * dasha and today's transits, so a new day asks again. */
  private suggestionCache = new Map<string, Promise<AskSuggestionsPayload>>();

  suggestions(kundliId: string, mode: string): Promise<AskSuggestionsPayload> {
    const key = `${kundliId}:${mode}:${new Date().toDateString()}`;
    let cached = this.suggestionCache.get(key);
    if (!cached) {
      cached = this.api.get<AskSuggestionsPayload>(`/ask/${kundliId}/suggestions?mode=${encodeURIComponent(mode)}`);
      // A failed request is not remembered; the next visit tries again.
      cached.catch(() => this.suggestionCache.delete(key));
      this.suggestionCache.set(key, cached);
    }
    return cached;
  }

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
    const threadId = this.threads.get(kundliId);
    history.update((msgs) => [...msgs, { role: 'user', content: question }]);
    this.pending.set(true);
    try {
      const res = await this.api.post<AskResponse>(`/ask/${kundliId}`, {
        question,
        ...(threadId ? { thread_id: threadId } : { start_thread: true }),
        language: this.preferences.language(),
        experience_mode: this.preferences.experienceMode(),
        tone: this.preferences.tone(),
      });
      if (res.thread_id) this.threads.set(kundliId, res.thread_id);
      history.update((msgs) => [
        ...msgs,
        {
          role: 'assistant',
          content: res.answer,
          tools: res.tools_used,
          status: res.status,
          refer_out_kind: res.refer_out_kind,
        },
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
      experience_mode?: 'guided' | 'balanced' | 'practitioner';
      /** The reader's gentle/direct preference; delivery only, like experience_mode. */
      tone?: 'gentle' | 'direct';
      input_mode?: 'text' | 'voice';
      /** An explicit domain the reader chose (a clarification chip) —
       * bypasses keyword routing server-side rather than being folded back
       * into `question` as prose. See AskOrchestrator.route()'s docstring:
       * the router only checks whether a keyword appears at least once, so
       * repeating "career" in a question that already said it once doesn't
       * change anything, and a tie against another domain never resolves. */
      domain_override?: string;
    },
    signal?: AbortSignal,
  ): AsyncGenerator<AskStreamEvent> {
    const token = await this.auth.getAccessToken();
    const response = await fetch(apiUrl(`/api/v1/ask/${encodeURIComponent(kundliId)}/stream`), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
      signal,
    });
    if (!response.ok || !response.body) {
      const text = await response.text().catch(() => '');
      if (response.status === 402) {
        try {
          const denial = JSON.parse(text);
          if (isEntitlementDenial(denial)) throw new EntitlementLimitError(denial);
        } catch (error) {
          if (error instanceof EntitlementLimitError) throw error;
        }
      }
      const detail = (() => {
        try {
          const parsed = JSON.parse(text);
          return parsed.detail || parsed.message || text;
        } catch {
          return text;
        }
      })();
      throw new Error(
        typeof detail === 'string' && detail.trim()
          ? detail
          : `Ask stream failed (${response.status})`,
      );
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
