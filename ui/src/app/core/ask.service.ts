import { Injectable, inject, signal } from '@angular/core';

import { ApiService } from './api.service';
import { AskMessage, AskResponse } from './models';

export const TOOL_LABELS: Record<string, string> = {
  get_birth_chart: 'Birth chart',
  get_varga_chart: 'Varga chart',
  get_today_panchanga: 'Panchanga',
  get_current_gochara: 'Gochara',
};

@Injectable({ providedIn: 'root' })
export class AskService {
  private api = inject(ApiService);

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
}
