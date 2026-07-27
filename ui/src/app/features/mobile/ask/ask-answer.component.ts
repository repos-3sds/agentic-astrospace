import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AskComposerComponent } from './ask-composer.component';
import {
  EvidenceRow,
  WhyReadingSheetComponent,
} from '../why-reading/why-reading-sheet.component';
import { MobileAskStateService } from './mobile-ask-state.service';
import { MobileAskThreadService } from './mobile-ask-thread.service';
import { KundliStore } from '../../../core/kundli.store';

/**
 * How confidently the answer lands. Named, not a number: the point of the dot
 * beside the verdict is that a reader can see the difference at a glance.
 */
export type VerdictTone = 'good' | 'warn' | 'bad';

export interface AnswerView {
  question: string;
  /** The domain the question was routed to — shown so a misroute is visible. */
  domain: string;
  tone: VerdictTone;
  verdict: string;
  whatToDo: string;
  followUps: string[];
}

/**
 * Ask — Answer view (Figma node 26:54).
 *
 * The verdict is one sentence and it comes first. The design puts WHAT TO DO
 * directly under it because an answer a reader cannot act on is not an answer;
 * everything explaining *how* the answer was reached is behind "Why this?",
 * which is Epic J's evidence surface rather than a second reading.
 *
 * Career, timing and money-as-timing are answerable here. Questions that ask
 * for a medical, legal or financial verdict — or about death or longevity — are
 * routed to the refer-out screen (27:83) instead of being answered softly.
 */
@Component({
  selector: 'as-ask-answer',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [AskComposerComponent, RouterLink, WhyReadingSheetComponent],
  templateUrl: './ask-answer.component.html',
  styleUrl: './ask-answer.component.scss',
})
export class AskAnswerComponent {
  private readonly askState = inject(MobileAskStateService);
  // The observable, not the snapshot: a follow-up re-enters this same route, and
  // Angular reuses the component rather than rebuilding it — read once and the
  // thread would answer the second question with the first one's text.
  private readonly params = toSignal(inject(ActivatedRoute).queryParamMap, {
    requireSync: true,
  });

  readonly view = computed<AnswerView>(() => ({
    question: this.params().get('q') ?? 'Is this a good time to change my job?',
    domain: 'CAREER',
    tone: 'good',
    verdict: this.askState.answer(this.params().get('thread'))
      ?? 'Yes — the next 6 weeks favour a change.',
    whatToDo: this.askState.answer(this.params().get('thread'))
      ? 'Use this as reflective guidance, then decide with the real-world information available to you.'
      : 'Start conversations and send applications this week — Thursday & Friday mornings are best. Wait to sign anything until after the 14th.',
    followUps: ['What about starting a business instead?'],
  }));

  readonly draft = signal('');
  readonly submitting = signal(false);
  readonly submitError = signal<string | null>(null);

  /**
   * The same evidence sheet Today uses (22:23). An answer and a day-reading owe
   * the reader the same account of themselves, and two sheets saying it two
   * ways is how the conventions start disagreeing.
   */
  readonly whyOpen = signal(false);

  readonly plainWords = signal([
    'Your Saturn period rewards steady moves over sudden ones.',
    'Jupiter is aspecting your 10th until the middle of next month.',
  ]);

  readonly calculation = signal<EvidenceRow[]>([
    { label: 'Active period', value: 'Venus – Saturn' },
    { label: '10th lord', value: 'Mercury · strong' },
    { label: 'Key gochara', value: 'Jupiter on 10th' },
  ]);

  readonly conventions = signal(['Lahiri', 'Whole-sign', 'Vijayawada', 'High confidence']);

  private readonly router = inject(Router);
  private readonly kundlis = inject(KundliStore);
  private readonly threadsApi = inject(MobileAskThreadService);

  /** Persists a follow-up in the open thread before displaying its answer. */
  protected async askAgain(question: string): Promise<void> {
    const q = question.trim();
    const threadId = this.params().get('thread');
    if (!q || !threadId || this.submitting()) return;

    this.submitting.set(true);
    this.submitError.set(null);
    try {
      await this.kundlis.load();
      const profile = this.kundlis.active();
      if (!profile) throw new Error('Select a profile before asking a follow-up.');

      const response = await this.threadsApi.continue(profile.id, threadId, q);
      this.askState.remember(response);
      const destination = response.refer_out_kind ? 'refer' : 'answer';
      await this.router.navigate(['/m', 'ask', destination], {
        queryParams: {
          q,
          thread: response.thread_id ?? threadId,
          domain: response.refer_out_kind ?? undefined,
        },
      });
      this.draft.set('');
    } catch (error) {
      this.submitError.set((error as Error).message);
    } finally {
      this.submitting.set(false);
    }
  }
}
