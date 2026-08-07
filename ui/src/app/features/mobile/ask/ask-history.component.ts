import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
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
  private readonly router = inject(Router);

  readonly threads = signal<MobileAskThread[]>([]);
  readonly loading = signal(true);
  readonly opening = signal<string | null>(null);
  readonly archiving = signal<string | null>(null);
  readonly revealedThreadId = signal<string | null>(null);
  readonly error = signal<string | null>(null);
  private touchStartX = 0;

  constructor() {
    void this.load();
  }

  protected async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
      const profile = this.kundlis.active();
      if (!profile) {
        this.threads.set([]);
        return;
      }
      const rows = await this.threadsApi.list(profile.id);
      this.threads.set(rows);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  protected async open(thread: MobileAskThread): Promise<void> {
    if (this.revealedThreadId() === thread.id) {
      this.revealedThreadId.set(null);
      return;
    }
    if (this.opening()) return;
    this.opening.set(thread.id);
    this.error.set(null);
    try {
      await this.router.navigate(['/m', 'ask', 'answer'], {
        queryParams: {
          thread: thread.id,
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
      if (this.revealedThreadId() === thread.id) this.revealedThreadId.set(null);
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

  protected beginSwipe(event: TouchEvent): void {
    this.touchStartX = event.touches[0]?.clientX ?? 0;
  }

  protected endSwipe(event: TouchEvent, thread: MobileAskThread): void {
    const endX = event.changedTouches[0]?.clientX ?? this.touchStartX;
    const deltaX = endX - this.touchStartX;
    if (deltaX > 44) {
      this.revealedThreadId.set(thread.id);
    } else if (deltaX < -24) {
      this.revealedThreadId.set(null);
    }
    this.touchStartX = 0;
  }
}
