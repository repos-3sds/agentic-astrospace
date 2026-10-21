import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { LucideAngularModule } from 'lucide-angular';

import { AdminService, AnswerReportRow, AnswerReports } from '../../core/admin.service';

const REASON_LABELS: Record<AnswerReportRow['reason'], string> = {
  wrong: 'Wrong or made up',
  harmful: 'Harmful or frightening',
  offensive: 'Rude or offensive',
  advice: 'Health, legal or money advice',
  other: 'Something else',
};

type Filter = 'open' | 'reviewed' | 'all';

/**
 * Readers' "Report this answer" on Ask, for full administrators. Each report
 * carries the question and answer as the reader saw them; marking one
 * reviewed only moves it out of the open list.
 */
@Component({
  selector: 'app-admin-answer-reports',
  imports: [DatePipe, LucideAngularModule],
  template: `
    <section class="bar">
      <div class="filters" role="group" aria-label="Show reports">
        @for (f of filters; track f.id) {
          <button type="button" [class.on]="filter() === f.id" [attr.aria-pressed]="filter() === f.id" (click)="load(f.id)">
            {{ f.label }}
          </button>
        }
      </div>
      <span class="count">{{ data()?.open ?? 0 }} open</span>
      <button type="button" class="refresh" (click)="load(filter())">
        <lucide-icon name="refresh-cw" [size]="15" /> Refresh
      </button>
    </section>

    @if (error()) {
      <p class="error" role="alert">{{ error() }}</p>
    }

    <div class="list">
      @for (r of data()?.reports ?? []; track r.id) {
        <article class="report" [attr.data-status]="r.status">
          <header>
            <span class="reason" [attr.data-reason]="r.reason">{{ reasonLabel(r.reason) }}</span>
            <span class="who">{{ r.email || ('reader ' + r.user_id.slice(0, 8)) }}</span>
            <span class="when">{{ r.created_at | date: 'MMM d, HH:mm' }}</span>
          </header>
          @if (r.note) {
            <p class="note">“{{ r.note }}”</p>
          }
          @if (r.question) {
            <p class="label">Question</p>
            <p class="question">{{ r.question }}</p>
          }
          <p class="label">Answer they saw</p>
          <pre class="answer">{{ r.answer }}</pre>
          <footer>
            <small>
              {{ r.experience_mode || 'balanced' }} · {{ r.language || 'en' }}
              @if (r.thread_id) { · thread {{ r.thread_id.slice(0, 8) }} } @else { · conversation not linked }
              @if (r.reviewed_at) { · reviewed {{ r.reviewed_at | date: 'MMM d, HH:mm' }} by {{ r.reviewed_by }} }
            </small>
            <button type="button" [disabled]="busy() === r.id" (click)="toggle(r)">
              {{ r.status === 'open' ? 'Mark reviewed' : 'Reopen' }}
            </button>
          </footer>
        </article>
      } @empty {
        <div class="empty">{{ loading() ? 'Loading…' : 'No reports here.' }}</div>
      }
    </div>
  `,
  styles: `
    :host { display: block; }
    .bar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
    .filters { display: inline-flex; border: 1px solid var(--as-border); border-radius: 8px; overflow: hidden; }
    .filters button { border: 0; padding: 7px 12px; background: var(--as-surface); color: var(--as-muted); font: inherit; font-size: 12px; cursor: pointer; }
    .filters button.on { background: var(--as-accent-soft); color: var(--as-accent-strong); font-weight: 700; }
    .count { color: var(--as-muted); font-size: 12px; margin-right: auto; }
    .refresh, footer button { display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--as-border); border-radius: 8px; padding: 7px 12px; background: var(--as-control); color: var(--as-text); font: inherit; font-size: 12px; cursor: pointer; }
    .error { color: var(--as-bad); }
    .list { display: grid; gap: 12px; }
    .report { border: 1px solid var(--as-border); border-radius: 8px; background: var(--as-surface); padding: 14px 16px; display: grid; gap: 6px; }
    .report[data-status='reviewed'] { opacity: .72; }
    header { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .reason { padding: 3px 8px; border-radius: 999px; font-size: 11px; font-weight: 800; color: var(--as-warn); background: var(--as-warn-soft); }
    .reason[data-reason='harmful'], .reason[data-reason='offensive'] { color: var(--as-bad); background: var(--as-bad-soft); }
    .who { font-weight: 700; font-size: 13px; color: var(--as-text); }
    .when { color: var(--as-muted); font-size: 12px; margin-left: auto; }
    .note { margin: 2px 0; font-size: 13px; color: var(--as-text); font-style: italic; }
    .label { margin: 6px 0 0; color: var(--as-muted); font-size: 10px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
    .question { margin: 0; font-size: 13px; color: var(--as-text); }
    .answer { margin: 0; max-height: 260px; overflow: auto; white-space: pre-wrap; font: inherit; font-size: 12.5px; line-height: 1.5; color: var(--as-text); background: var(--as-control); border-radius: 6px; padding: 10px 12px; }
    footer { display: flex; align-items: center; gap: 12px; margin-top: 4px; }
    footer small { color: var(--as-muted); font-size: 11px; margin-right: auto; }
    .empty { padding: 28px; text-align: center; color: var(--as-muted); border: 1px dashed var(--as-border); border-radius: 8px; }
  `,
})
export class AdminAnswerReportsComponent implements OnInit {
  private readonly admin = inject(AdminService);

  protected readonly filters: { id: Filter; label: string }[] = [
    { id: 'open', label: 'Open' },
    { id: 'reviewed', label: 'Reviewed' },
    { id: 'all', label: 'All' },
  ];
  protected readonly filter = signal<Filter>('open');
  protected readonly data = signal<AnswerReports | null>(null);
  protected readonly loading = signal(false);
  protected readonly busy = signal<string | null>(null);
  protected readonly error = signal('');

  ngOnInit(): void {
    void this.load('open');
  }

  protected reasonLabel(reason: AnswerReportRow['reason']): string {
    return REASON_LABELS[reason] ?? reason;
  }

  protected async load(filter: Filter): Promise<void> {
    this.filter.set(filter);
    this.loading.set(true);
    this.error.set('');
    try {
      this.data.set(await this.admin.answerReports(filter));
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  protected async toggle(report: AnswerReportRow): Promise<void> {
    this.busy.set(report.id);
    try {
      await this.admin.setAnswerReportStatus(report.id, report.status === 'open' ? 'reviewed' : 'open');
      await this.load(this.filter());
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.busy.set(null);
    }
  }
}
