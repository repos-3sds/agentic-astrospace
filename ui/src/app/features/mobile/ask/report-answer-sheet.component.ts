import { ChangeDetectionStrategy, Component, inject, input, output, signal } from '@angular/core';

import { SheetComponent } from '../sheet/sheet.component';
import { AnswerReport, AnswerReportReason, MobileAskThreadService } from './mobile-ask-thread.service';

/** What the answer screen knows about the answer being reported. */
export type AnswerReportContext = Omit<AnswerReport, 'reason' | 'note'>;

export const REPORT_REASONS: { id: AnswerReportReason; label: string; detail: string }[] = [
  { id: 'wrong', label: 'Wrong or made up', detail: 'It does not match my chart or the facts' },
  { id: 'harmful', label: 'Harmful or frightening', detail: 'It could scare or hurt someone' },
  { id: 'offensive', label: 'Rude or offensive', detail: 'Unkind words, or about caste, religion or gender' },
  { id: 'advice', label: 'Health, legal or money advice', detail: 'Siddha should not advise on these' },
  { id: 'other', label: 'Something else', detail: 'Tell us in the note below' },
];

const NOTE_LIMIT = 1000;

/**
 * "Report this answer" on Ask. Google Play asks every app with AI-generated
 * content to let readers flag an answer without leaving the app. The reader
 * picks one reason, may add a note, and the team gets an email and reads the
 * answer in Admin (astrospace/api/ask_routes.py report_answer).
 */
@Component({
  selector: 'as-report-answer-sheet',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SheetComponent],
  template: `
    <as-sheet (dismissed)="dismissed.emit()">
      @if (sent()) {
        <header class="head">
          <h2 class="title">Thank you</h2>
          <p class="sub">We have your report. Our team will read this answer and use it to make Siddha better.</p>
        </header>
        <button class="send" type="button" (click)="dismissed.emit()">Done</button>
      } @else {
        <header class="head">
          <h2 class="title">Report this answer</h2>
          <p class="sub">Tell us what went wrong. A person on our team reads every report.</p>
        </header>

        <div class="reasons" role="radiogroup" aria-label="What is wrong with this answer?">
          @for (r of reasons; track r.id) {
            @let on = reason() === r.id;
            <button
              class="reason"
              type="button"
              role="radio"
              [class.is-on]="on"
              [attr.aria-checked]="on"
              (click)="reason.set(r.id)"
            >
              <span class="reason-copy">
                <span class="reason-label">{{ r.label }}</span>
                <small>{{ r.detail }}</small>
              </span>
              @if (on) {
                <span class="tick" aria-hidden="true"><img src="mobile/check.svg" alt="" /></span>
              } @else {
                <img class="radio" src="mobile/radio-off.svg" alt="" aria-hidden="true" />
              }
            </button>
          }
        </div>

        <label class="note">
          <span>Anything to add? (optional)</span>
          <textarea
            rows="3"
            [maxLength]="noteLimit"
            placeholder="What was wrong in the answer?"
            [value]="note()"
            (input)="note.set($any($event.target).value)"
          ></textarea>
        </label>

        @if (error()) {
          <p class="error" role="alert">{{ error() }}</p>
        }

        <button class="send" type="button" [disabled]="!reason() || sending()" (click)="send()">
          {{ sending() ? 'Sending…' : 'Send report' }}
        </button>
      }
    </as-sheet>
  `,
  styles: `
    @use '../mobile-tokens' as *;
    :host { display: contents; }
    .head { display: flex; flex-direction: column; gap: 4px; }
    .title { @include m-h2; color: var(--m-text); margin: 0; }
    .sub { @include m-body-small; color: var(--m-muted); margin: 0; }
    .reasons { display: flex; flex-direction: column; gap: 8px; }
    .reason {
      width: 100%;
      box-sizing: border-box;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      min-height: 56px;
      padding: 10px 14px;
      border: 1.2px solid var(--m-border);
      border-radius: 16px;
      background: var(--m-surface);
      color: var(--m-text);
      text-align: left;
      cursor: pointer;
      &.is-on {
        border: 2px solid var(--m-accent);
        background: var(--m-accent-soft);
      }
    }
    .reason-copy { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
    .reason-label { @include m-body-strong; }
    .reason small { @include m-caption; color: var(--m-muted); }
    .radio { width: 22px; height: 22px; display: block; flex-shrink: 0; }
    .tick {
      width: 22px;
      height: 22px;
      border-radius: 999px;
      background: var(--m-accent);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      img { width: 13px; height: 13px; display: block; }
    }
    .note {
      display: flex;
      flex-direction: column;
      gap: 6px;
      span { @include m-body-small; color: var(--m-text); }
      textarea {
        @include m-body-small;
        width: 100%;
        box-sizing: border-box;
        min-height: 76px;
        resize: none;
        border: 1px solid var(--m-border);
        border-radius: 14px;
        padding: 10px 12px;
        background: var(--m-surface);
        color: var(--m-text);
        font: inherit;
        outline: none;
      }
      textarea::placeholder { color: var(--m-muted); }
      textarea:focus { border-color: var(--m-accent); }
    }
    .error { @include m-body-small; color: var(--m-bad); margin: 0; }
    .send { @include m-cta-primary; width: 100%; }
    .send:disabled { opacity: 0.5; cursor: default; }
  `,
})
export class ReportAnswerSheetComponent {
  private readonly threads = inject(MobileAskThreadService);

  readonly context = input.required<AnswerReportContext>();
  readonly dismissed = output<void>();
  /** Emitted once the server has the report. */
  readonly reported = output<void>();

  protected readonly reasons = REPORT_REASONS;
  protected readonly noteLimit = NOTE_LIMIT;
  protected readonly reason = signal<AnswerReportReason | null>(null);
  protected readonly note = signal('');
  protected readonly sending = signal(false);
  protected readonly sent = signal(false);
  protected readonly error = signal<string | null>(null);

  protected async send(): Promise<void> {
    const reason = this.reason();
    if (!reason || this.sending()) return;
    this.sending.set(true);
    this.error.set(null);
    try {
      await this.threads.report({
        ...this.context(),
        reason,
        note: this.note().trim().slice(0, NOTE_LIMIT) || null,
      });
      this.sent.set(true);
      this.reported.emit();
    } catch (error) {
      this.error.set((error as Error).message || 'Your report could not be sent. Please try again.');
    } finally {
      this.sending.set(false);
    }
  }
}
