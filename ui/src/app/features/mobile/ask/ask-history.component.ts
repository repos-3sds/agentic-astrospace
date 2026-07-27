import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { MobileAskStateService } from './mobile-ask-state.service';
import {
  MobileAskThread,
  MobileAskThreadService,
} from './mobile-ask-thread.service';

@Component({
  selector: 'as-ask-history',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './ask-history.component.html',
  styleUrl: './ask-history.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AskHistoryComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly threadsApi = inject(MobileAskThreadService);
  private readonly askState = inject(MobileAskStateService);
  private readonly router = inject(Router);

  readonly threads = signal<MobileAskThread[]>([]);
  readonly loading = signal(true);
  readonly opening = signal<string | null>(null);
  readonly archiving = signal<string | null>(null);
  readonly error = signal<string | null>(null);

  constructor() {
    void this.load();
  }

  protected async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
      const profile = this.kundlis.active();
      this.threads.set(profile ? await this.threadsApi.list(profile.id) : []);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  protected async open(thread: MobileAskThread): Promise<void> {
    if (this.opening()) return;
    this.opening.set(thread.id);
    this.error.set(null);
    try {
      const detail = await this.threadsApi.get(thread.id);
      const question = detail.messages.find((message) => message.role === 'user');
      const answer = [...detail.messages]
        .reverse()
        .find((message) => message.role === 'assistant');
      if (!question || !answer) throw new Error('This conversation has no answer yet.');

      this.askState.rememberAnswer(thread.id, answer.content);
      const destination = answer.refer_out_kind ? 'refer' : 'answer';
      await this.router.navigate(['/m', 'ask', destination], {
        queryParams: {
          q: question.content,
          thread: thread.id,
          domain: answer.refer_out_kind ?? undefined,
        },
      });
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.opening.set(null);
    }
  }

  protected async archive(event: Event, thread: MobileAskThread): Promise<void> {
    event.stopPropagation();
    if (this.archiving()) return;
    this.archiving.set(thread.id);
    this.error.set(null);
    try {
      await this.threadsApi.archive(thread.id);
      this.threads.update((items) => items.filter((item) => item.id !== thread.id));
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.archiving.set(null);
    }
  }

  protected date(thread: MobileAskThread): string {
    const value = thread.last_message_at ?? thread.created_at;
    if (!value) return 'Saved conversation';
    return new Intl.DateTimeFormat('en-GB', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
    }).format(new Date(value));
  }
}
