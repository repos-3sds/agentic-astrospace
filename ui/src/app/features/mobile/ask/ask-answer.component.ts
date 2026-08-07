import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AskComposerComponent } from './ask-composer.component';
import { ListenSheetComponent } from '../today/listen-sheet.component';
import {
  EvidenceRow,
  SourceReference,
  WhyReadingSheetComponent,
} from '../why-reading/why-reading-sheet.component';
import { MobileAskStateService } from './mobile-ask-state.service';
import { AskService } from '../../../core/ask.service';
import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';

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
  preview: boolean;
}

interface AnswerSection {
  title: string;
  body: string;
}

const REFER_OUT_KINDS = new Set(['death', 'health', 'legal', 'money']);
const INLINE_SECTION_RE =
  /(^|[.!?])\s+((?:The timing|Timing|Career signal|Main signal|What this means|What to do|Use care|Astrological basis|Basis|Recommendation|Bottom line|Verdict|Gochara|Remedy)[^.!?\n]{0,80}:)/gi;

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
 *
 * This screen owns the actual call to the orchestrator (POST
 * /ask/{kundliId}/stream, ask_stream_routes.py): both a fresh question from
 * Ask Home and a follow-up typed here land on this same route with a new `q`
 * (and `thread` once one exists), and an effect reacting to those query
 * params is what triggers `startStream` — one trigger point instead of two
 * different code paths for "first question" and "follow-up".
 */
@Component({
  selector: 'as-ask-answer',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [AskComposerComponent, ListenSheetComponent, RouterLink, WhyReadingSheetComponent],
  templateUrl: './ask-answer.component.html',
  styleUrl: './ask-answer.component.scss',
})
export class AskAnswerComponent {
  protected readonly preferences = inject(PreferencesService);
  private readonly askState = inject(MobileAskStateService);
  private readonly askService = inject(AskService);
  private readonly kundlis = inject(KundliStore);
  private readonly router = inject(Router);
  // The observable, not the snapshot: a follow-up re-enters this same route, and
  // Angular reuses the component rather than rebuilding it — read once and the
  // thread would answer the second question with the first one's text.
  private readonly params = toSignal(inject(ActivatedRoute).queryParamMap, {
    requireSync: true,
  });

  readonly streaming = signal(false);
  readonly streamedAnswer = signal('');
  readonly streamDomain = signal<string | null>(null);
  readonly streamEvidence = signal<SourceReference[]>([]);

  readonly view = computed<AnswerView>(() => {
    const question = this.params().get('q') ?? 'What should I know right now?';
    const streamed = this.streamedAnswer();
    if (this.streaming() || streamed) {
      return {
        question,
        domain: (this.streamDomain() ?? '…').toUpperCase(),
        tone: 'good',
        verdict: streamed || 'Reading your chart…',
        whatToDo: 'Use this as reflective guidance, then decide with the real-world information available to you.',
        followUps: this.streaming() ? [] : ['Ask a follow-up about timing', 'Show the chart factors behind this'],
        preview: false,
      };
    }

    const savedAnswer = this.askState.answer(this.params().get('thread'));
    if (savedAnswer) {
      return {
        question,
        domain: 'GUIDANCE',
        tone: 'good',
        verdict: savedAnswer,
        whatToDo: 'Use this as reflective guidance, then decide with the real-world information available to you.',
        followUps: ['Ask a follow-up about timing', 'Show the chart factors behind this'],
        preview: false,
      };
    }

    // Reached only if this route loads with no `q` at all — the two real
    // entry points (Ask Home's composer, Ask History) always supply one.
    return {
      question,
      domain: 'PREVIEW',
      tone: 'warn',
      verdict: 'Ask a question to get started.',
      whatToDo: 'Head back to Ask and type what is on your mind.',
      followUps: [],
      preview: true,
    };
  });
  readonly listenScript = computed(() => {
    const v = this.view();
    return `${v.question}. ${v.verdict} ${v.whatToDo}`;
  });
  readonly answerCopy = computed(() => this.copyFromAnswer(this.view().verdict));

  readonly draft = signal('');
  readonly submitError = signal<string | null>(null);

  /**
   * The same evidence sheet Today uses (22:23). An answer and a day-reading owe
   * the reader the same account of themselves, and two sheets saying it two
   * ways is how the conventions start disagreeing.
   */
  readonly whyOpen = signal(false);

  /** Sentence-split of the real streamed answer — not a separate backend
   * field, but genuinely the reasoning the reader is asking to see again. */
  readonly plainWords = computed<string[]>(() => {
    const text = this.normaliseAnswerText(this.streamedAnswer()).trim();
    if (!text) return [];
    return text.split(/(?<=[.!?])\s+/).filter((s) => s.length > 0);
  });

  readonly calculation = computed<EvidenceRow[]>(() => {
    const domain = this.streamDomain();
    return domain ? [{ label: 'Routed to', value: domain[0].toUpperCase() + domain.slice(1) }] : [];
  });

  /** Real classical-text citations from the assembled bundle — see
   * ask_stream_routes.py's `_evidence_from_bundle`. Empty until routing has
   * actually happened once, which is honest: there is nothing to cite yet. */
  readonly references = computed<SourceReference[]>(() => this.streamEvidence());

  readonly conventions = computed<string[]>(() => {
    const domain = this.streamDomain();
    return [this.preferences.ayanamsha(), ...(domain ? [domain.toUpperCase()] : [])];
  });
  protected readonly whyMode = computed(() => ({
    guided: 'Guided view — a short cause-and-effect explanation.',
    balanced: 'Balanced view — plain first, the calculation underneath.',
    practitioner: 'Practitioner view — scoped inputs, factors, and provenance.',
  })[this.preferences.experienceMode()]);

  /** Reuses Today's audio sheet — one player, not a second one for answers. */
  readonly listenOpen = signal(false);

  /** Guards against re-streaming the same (thread, question) pair when the
   * effect below re-fires — e.g. once `startStream` updates the URL with a
   * freshly created thread id. */
  private lastStreamedKey: string | null = null;
  /** True once this component instance has kicked off a stream at least
   * once. Distinguishes "a follow-up in a thread we're already streaming
   * in" (must always stream) from "landed here via Ask History, which
   * pre-fetched a real answer and remembered it before navigating" (must
   * not re-stream) — both cases can otherwise present the same threadId
   * with `askState.answer(threadId)` already populated. */
  private hasStreamedInThisInstance = false;

  private copyFromAnswer(answer: string): { lead: string; sections: AnswerSection[] } {
    const text = this.normaliseAnswerText(answer);
    if (!text) return { lead: '', sections: [] };
    if (text === 'Reading your chart…' || text === 'Ask a question to get started.') {
      return { lead: text, sections: [] };
    }

    const lines = text
      .replace(INLINE_SECTION_RE, (_match, boundary: string, heading: string) => `${boundary}\n${heading}`)
      .split(/\n+/)
      .map((line) => line.trim())
      .filter(Boolean);

    const leadParts: string[] = [];
    const sections: AnswerSection[] = [];
    let current: AnswerSection | null = null;

    for (const line of lines) {
      const heading = this.extractHeading(line);
      if (heading) {
        if (current) sections.push(current);
        current = { title: heading.title, body: heading.body };
        continue;
      }
      if (current) {
        current.body = [current.body, line].filter(Boolean).join(' ');
      } else {
        leadParts.push(line);
      }
    }
    if (current) sections.push(current);

    const leadSource = leadParts.join(' ') || sections.shift()?.body || text;
    const leadSentences = this.sentences(leadSource);
    const splitLead = this.splitLead(leadSentences[0] || leadSource);
    const lead = splitLead.lead;
    const leadRemainder = [splitLead.remainder, ...leadSentences.slice(1)]
      .filter(Boolean)
      .join(' ');
    if (leadRemainder) {
      sections.unshift({ title: 'Summary', body: leadRemainder });
    }

    return {
      lead,
      sections: sections
        .map((section) => ({
          title: section.title,
          body: section.body.trim(),
        }))
        .filter((section) => section.body),
    };
  }

  private normaliseAnswerText(answer: string): string {
    return answer
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/__(.*?)__/g, '$1')
      .replace(/^\s{0,3}#{1,6}\s*/gm, '')
      .replace(/^\s*[-*]\s+/gm, '')
      .replace(/\s+/g, ' ')
      .replace(/\s+([,.;:!?])/g, '$1')
      .trim();
  }

  private extractHeading(line: string): AnswerSection | null {
    const match = line.match(/^([^:]{3,86}):\s*(.*)$/);
    if (!match) return null;
    const title = match[1]
      .replace(/^[0-9]+[.)]\s*/, '')
      .trim();
    if (!/[A-Za-z]/.test(title)) return null;
    return { title, body: match[2].trim() };
  }

  private sentences(text: string): string[] {
    return text
      .split(/(?<=[.!?])\s+/)
      .map((sentence) => sentence.trim())
      .filter(Boolean);
  }

  private splitLead(sentence: string): { lead: string; remainder: string } {
    if (sentence.length <= 145) return { lead: sentence, remainder: '' };
    const candidates = [' for ', ' with ', ' because ', ' while ', ' as ']
      .map((needle) => sentence.indexOf(needle, 88))
      .filter((index) => index > 0 && index <= 150);
    const cut = candidates.length ? Math.min(...candidates) : sentence.lastIndexOf(',', 145);
    if (cut < 80) return { lead: sentence, remainder: '' };
    const lead = sentence.slice(0, cut).replace(/[,.]\s*$/, '').trim() + '.';
    const remainder = sentence.slice(cut).trim().replace(/^[,.;:-]\s*/, '');
    return {
      lead,
      remainder: remainder ? remainder[0].toUpperCase() + remainder.slice(1) : '',
    };
  }

  constructor() {
    effect(() => {
      const question = this.params().get('q');
      const threadId = this.params().get('thread');
      if (!question) return;
      const key = `${threadId ?? ''}::${question}`;
      if (key === this.lastStreamedKey) return;
      if (!this.hasStreamedInThisInstance && threadId && this.askState.answer(threadId)) {
        this.lastStreamedKey = key;
        return;
      }
      this.lastStreamedKey = key;
      this.hasStreamedInThisInstance = true;
      void this.startStream(question, threadId);
    });
  }

  private async startStream(question: string, threadId: string | null): Promise<void> {
    await this.kundlis.load();
    const profile = this.kundlis.active();
    if (!profile) {
      this.submitError.set('Select a profile before asking a question.');
      return;
    }

    this.streaming.set(true);
    this.streamedAnswer.set('');
    this.streamDomain.set(null);
    this.streamEvidence.set([]);
    this.submitError.set(null);

    try {
      let finalThreadId: string | null = threadId;
      let referOutKind: string | null = null;
      for await (const event of this.askService.stream(profile.id, {
        question,
        thread_id: threadId ?? undefined,
        start_thread: true,
        input_mode: 'text',
      })) {
        if ('delta' in event) {
          this.streamedAnswer.set(event.reset ? event.delta : this.streamedAnswer() + event.delta);
        } else {
          finalThreadId = event.thread_id;
          referOutKind = event.refer_out_kind;
          this.streamDomain.set(event.domain);
          this.streamEvidence.set(event.evidence);
          if (finalThreadId) this.askState.rememberAnswer(finalThreadId, this.streamedAnswer());
        }
      }

      if (referOutKind && REFER_OUT_KINDS.has(referOutKind)) {
        await this.router.navigate(['/m', 'ask', 'refer'], {
          queryParams: { q: question, domain: referOutKind },
          replaceUrl: true,
        });
        return;
      }
      if (finalThreadId && finalThreadId !== threadId) {
        // Set before navigating: the URL change below re-fires the
        // constructor's effect, and it must recognise this exact
        // (thread, question) pair as already handled rather than stream it
        // a second time.
        this.lastStreamedKey = `${finalThreadId}::${question}`;
        await this.router.navigate(['/m', 'ask', 'answer'], {
          queryParams: { q: question, thread: finalThreadId },
          replaceUrl: true,
        });
      }
    } catch (error) {
      this.submitError.set((error as Error).message);
    } finally {
      this.streaming.set(false);
    }
  }

  /**
   * Hands the verdict to the OS share sheet where available. No fallback UI:
   * on a platform without it, doing nothing is better than inventing a
   * share dialog the design never specified.
   */
  protected async share(): Promise<void> {
    const v = this.view();
    if (typeof navigator !== 'undefined' && 'share' in navigator) {
      try {
        await navigator.share({ title: v.question, text: `${v.verdict}\n\n${v.whatToDo}` });
      } catch {
        // Cancelled by the reader; nothing to report.
      }
    }
  }

  /** Navigates to this same route with a new question — the constructor's
   * effect is what actually calls the orchestrator once params land. */
  protected async askAgain(question: string): Promise<void> {
    const q = question.trim();
    if (!q || this.streaming()) return;
    this.draft.set('');
    await this.router.navigate(['/m', 'ask', 'answer'], {
      queryParams: { q, thread: this.params().get('thread') ?? undefined },
    });
  }
}
