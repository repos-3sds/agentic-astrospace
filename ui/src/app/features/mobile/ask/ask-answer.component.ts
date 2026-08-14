import { ChangeDetectionStrategy, Component, computed, effect, inject, signal, untracked } from '@angular/core';
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
import { AskStreamEvent, AskTechnicalBasisItem, StructuredReading } from '../../../core/models';
import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';
import { MobileAskMessage, MobileAskThreadService } from './mobile-ask-thread.service';

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

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  domain: string | null;
  intent: string | null;
  status: string | null;
  refer_out_kind: string | null;
  created_at: string | null;
  evidence: SourceReference[];
  context_used: string[];
  evidence_refs: string[];
  profile_context_revision: number;
  profile_context_as_of: string | null;
  reading: StructuredReading | null;
  options: string[];
  streaming?: boolean;
}

const REFER_OUT_KINDS = new Set(['death', 'health', 'legal', 'money']);

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
  private readonly threadsApi = inject(MobileAskThreadService);
  private readonly kundlis = inject(KundliStore);
  private readonly router = inject(Router);
  // The observable, not the snapshot: a follow-up re-enters this same route, and
  // Angular reuses the component rather than rebuilding it — read once and the
  // thread would answer the second question with the first one's text.
  private readonly params = toSignal(inject(ActivatedRoute).queryParamMap, {
    requireSync: true,
  });

  readonly streaming = signal(false);
  readonly loadingThread = signal(false);
  readonly archivingThread = signal(false);
  readonly messages = signal<ChatMessage[]>([]);
  readonly streamedAnswer = signal('');
  readonly streamStatus = signal<string | null>(null);
  readonly streamDomain = signal<string | null>(null);
  readonly streamEvidence = signal<SourceReference[]>([]);
  protected readonly activeThreadId = signal<string | null>(null);
  private readonly selectedAssistant = signal<ChatMessage | null>(null);

  readonly assistantMessages = computed(() => this.messages().filter((message) => message.role === 'assistant'));
  readonly latestAssistant = computed(() => {
    const assistants = this.assistantMessages();
    return assistants.length ? assistants[assistants.length - 1] : null;
  });
  readonly latestUser = computed(() => {
    const users = this.messages().filter((message) => message.role === 'user');
    return users.length ? users[users.length - 1] : null;
  });
  /** The thread's original question, not the latest — a clarification chip
   * resolves what the reader first asked, not whatever text a previous
   * (now-removed) wrapping attempt may have left behind. */
  readonly firstUser = computed(() => {
    const users = this.messages().filter((message) => message.role === 'user');
    return users.length ? users[0] : null;
  });
  readonly latestFollowUps = computed(() => {
    const latest = this.latestAssistant();
    if (!latest || latest.status !== 'answered') return [];
    const readingFollowUps = latest.reading?.guidance.follow_up_questions ?? [];
    return readingFollowUps.length ? readingFollowUps : this.view().followUps;
  });

  readonly view = computed<AnswerView>(() => {
    const question = this.latestUser()?.content ?? this.params().get('q') ?? 'What should I know right now?';
    const assistant = this.latestAssistant();
    if (assistant) {
      return {
        question,
        domain: (assistant.domain ?? this.streamDomain() ?? '…').toUpperCase(),
        tone: 'good',
        verdict: assistant.content || 'Reading your chart…',
        whatToDo: 'Use this as reflective guidance, then decide with the real-world information available to you.',
        followUps: this.streaming()
          ? []
          : ['Which timing window is strongest?', 'What chart factors support this?'],
        preview: false,
      };
    }

    // Only a thread that has been fetched and verified against the active
    // profile may unlock session-cached content. Reading by the raw URL id
    // briefly exposed another profile's last answer while `loadThread()` was
    // still checking the thread.
    const savedAnswer = this.askState.answer(this.activeThreadId());
    if (savedAnswer) {
      return {
        question,
        domain: 'GUIDANCE',
        tone: 'good',
        verdict: savedAnswer,
        whatToDo: 'Use this as reflective guidance, then decide with the real-world information available to you.',
        followUps: ['Which timing window is strongest?', 'What chart factors support this?'],
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
    const message = this.selectedAssistant() ?? this.latestAssistant();
    const v = this.view();
    return `${v.question}. ${message?.content ?? v.verdict} ${v.whatToDo}`;
  });

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
    const message = this.selectedAssistant() ?? this.latestAssistant();
    if (message?.reading) {
      return [
        message.reading.acknowledgment,
        message.reading.interpretation,
        message.reading.summary_and_assurance,
      ].filter(Boolean);
    }
    return this.sentences(message?.content ?? this.streamedAnswer());
  });

  readonly calculation = computed<EvidenceRow[]>(() => {
    const message = this.selectedAssistant() ?? this.latestAssistant();
    if (message?.reading?.technical_basis?.length) {
      return message.reading.technical_basis.map((item) => ({
        label: item.factor,
        value: item.reading,
      }));
    }
    const domain = message?.domain ?? this.streamDomain();
    return domain ? [{ label: 'Routed to', value: this.titleCase(domain) }] : [];
  });

  /** Real classical-text citations from the assembled bundle — see
   * ask_stream_routes.py's `_evidence_from_bundle`. Empty until routing has
   * actually happened once, which is honest: there is nothing to cite yet. */
  readonly references = computed<SourceReference[]>(() => {
    const message = this.selectedAssistant() ?? this.latestAssistant();
    if (message?.reading?.technical_basis?.length) {
      return message.reading.technical_basis.map((item) => ({
        statement: item.factor,
        source_location: this.sourceLabel(item.source),
      }));
    }
    return message?.evidence?.length ? message.evidence : this.streamEvidence();
  });

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
  private lastRouteKey: string | null = null;
  private loadedThreadId: string | null = null;
  private threadLoadRevision = 0;
  private viewedProfileId: string | null | undefined = undefined;
  private abortController: AbortController | null = null;

  private normaliseAnswerText(answer: string): string {
    return answer
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/__(.*?)__/g, '$1')
      .replace(/^\s{0,3}#{1,6}\s*/gm, '')
      .replace(/^\s*[-*]\s+/gm, '• ')
      .replace(/[ \t]+/g, ' ')
      .replace(/\n{3,}/g, '\n\n')
      .replace(/\s+([,.;:!?])/g, '$1')
      .trim();
  }

  private sentences(text: string): string[] {
    const normalized = this.normaliseAnswerText(text);
    if (!normalized) return [];
    return normalized
      .split(/(?<=[.!?])\s+/)
      .map((sentence) => sentence.trim())
      .filter(Boolean);
  }

  private titleCase(value: string): string {
    return value
      .replace(/[_-]+/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  protected sourceLabel(source: StructuredReading['technical_basis'][number]['source']): string {
    if (!source) return 'Context Engine';
    if (typeof source === 'string') return this.titleCase(source);
    return [
      source.key,
      source.ref_id,
      source.chunk_id,
      source.section,
      source.location,
    ].filter(Boolean).map((item) => this.titleCase(String(item))).join(' · ') || 'Context Engine';
  }

  protected confidenceLabel(confidence: StructuredReading['confidence']): string {
    const normalized = String(confidence || 'medium').toLowerCase();
    if (normalized === 'high') return 'High confidence';
    if (normalized === 'low') return 'Low confidence';
    return 'Medium confidence';
  }

  protected confidenceTone(confidence: StructuredReading['confidence']): VerdictTone {
    const normalized = String(confidence || 'medium').toLowerCase();
    if (normalized === 'high') return 'good';
    if (normalized === 'low') return 'warn';
    return 'warn';
  }

  protected contextPills(message: ChatMessage): string[] {
    const mode = this.preferences.experienceMode();
    if (mode === 'guided') return [];
    const context = message.context_used?.length ? message.context_used : message.evidence_refs;
    return context
      .slice(0, mode === 'practitioner' ? 5 : 3)
      .map((item) => this.titleCase(item))
      .filter(Boolean);
  }

  /**
   * Whether the FULL `technical_basis` section (a labelled list of chart
   * factors) should render for this mode. Guided gets a single one-line
   * mention instead — see `guidedTechnicalHint` — never this section: per
   * The agent now writes each reading in the selected persona register. The
   * client must render that returned explanation in full; its own mode branch
   * changes technical disclosure and controls, not explanation completeness.
   */
  protected showTechnicalBasis(message: ChatMessage): boolean {
    if (!message.reading?.technical_basis?.length) return false;
    return this.preferences.experienceMode() !== 'guided';
  }

  /** Balanced gets a high-level subset (factor names + a compact reading,
   * still no full provenance detail); Practitioner gets the whole list,
   * granular. Guided never calls this — see `guidedTechnicalHint`. */
  protected technicalBasis(message: ChatMessage): AskTechnicalBasisItem[] {
    const items = message.reading?.technical_basis ?? [];
    return this.preferences.experienceMode() === 'practitioner' ? items : items.slice(0, 3);
  }

  /** Guided's "very less" technical disclosure: at most one line naming the
   * single strongest chart factor, not the full labelled list Balanced/
   * Practitioner get. Returns null when there is nothing to cite, in which
   * case Guided shows no technical line at all — "none or a single
   * one-line mention at most," never a full section. */
  protected guidedTechnicalHint(message: ChatMessage): string | null {
    const item = message.reading?.technical_basis?.[0];
    if (!item) return null;
    return this.compactSentence(`${item.factor}: ${item.reading}`, 100);
  }

  protected modeEyebrow(message: ChatMessage): string {
    if (message.status !== 'answered') {
      return `${this.answerLabel(message)} · ${
        (message.domain ?? (message.streaming ? this.streamDomain() : null) ?? 'GUIDANCE').toUpperCase()
      }`;
    }
    switch (this.preferences.experienceMode()) {
      case 'guided':
        return 'READING SUMMARY';
      case 'practitioner':
        return 'CHART SYNTHESIS';
      default:
        return 'BALANCED SUMMARY';
    }
  }

  protected practitionerScopeLine(message: ChatMessage): string {
    const domain = this.titleCase(message.domain ?? this.streamDomain() ?? 'Guidance');
    const context = message.context_used?.length ? message.context_used : message.evidence_refs;
    const scope = context.length ? context.slice(0, 3).map((item) => this.titleCase(item)).join(', ') : domain;
    return `Profile: Active · Scope: ${domain}${scope && scope !== domain ? ` (${scope})` : ''}`;
  }

  protected practitionerVerdictLabel(message: ChatMessage): string {
    const confidence = message.reading?.confidence ?? 'medium';
    if (String(confidence).toLowerCase() === 'high') return 'Favourable';
    if (String(confidence).toLowerCase() === 'low') return 'Needs care';
    return 'Qualified';
  }

  protected answerHeadline(message: ChatMessage): string {
    const reading = message.reading;
    if (!reading) return message.content || 'Reading your chart…';
    const source = reading.summary_and_assurance || reading.interpretation || reading.acknowledgment;
    return this.compactSentence(source, 150);
  }

  /** The interpretation as real paragraphs.
   *
   * The backend writes multi-paragraph consultations — the word cap was
   * deliberately removed from the domain agent's prompt ("prioritize
   * completeness and accuracy over brevity") — but this was rendered into a
   * single <p>, where HTML collapses the blank lines between paragraphs. A
   * 900-word reading arrived on screen as one unbroken slab, which is why
   * copying the answer read far better than looking at it: the clipboard
   * kept the structure the page threw away.
   *
   * Splitting here rather than adding `white-space: pre-wrap` is deliberate:
   * real <p> elements can carry their own spacing and reading measure, and
   * pre-wrap would also preserve every incidental single newline the model
   * happens to emit mid-sentence. */
  protected readingParagraphs(reading: StructuredReading): string[] {
    const text = this.normaliseAnswerText(reading.interpretation ?? '');
    return text
      .split(/\n\s*\n+/)
      .map((paragraph) => paragraph.replace(/\s*\n\s*/g, ' ').trim())
      .filter(Boolean);
  }

  /** Full `practical_actions` (falling back to `follow_up_questions` when
   * the reading has none) — the same list, unsliced, for Guided, Balanced,
   * and Practitioner alike. Was previously Guided-only and capped at 2
   * items (`guidedActions`). Each persona receives its own agent-written
   * guidance, and the client renders the complete returned list. */
  protected readingActions(reading: StructuredReading): string[] {
    const actions = reading.guidance.practical_actions.filter(Boolean);
    if (actions.length) return actions;
    return reading.guidance.follow_up_questions.map((question) => `Ask next: ${question}`);
  }

  private compactSentence(text: string, maxLength: number): string {
    const clean = this.normaliseAnswerText(text).replace(/\s+/g, ' ').trim();
    if (!clean) return '';
    const first = clean.match(/^(.+?[.!?])(\s|$)/)?.[1]?.trim() ?? clean;
    const candidate = first.length >= 18 ? first : clean;
    if (candidate.length <= maxLength) return candidate;
    // Prefer a clause boundary over a word boundary. This is the most
    // prominent line on the screen, and clipping it mid-phrase reads as
    // broken rather than abbreviated — the shipped app showed "…it is
    // engineered for enduring…", which stops on a preposition. Ending at
    // the last semicolon or comma instead gives a fragment that reads as a
    // deliberate headline: "Your chart is not built for fleeting,
    // superficial success".
    const window = candidate.slice(0, maxLength - 1);
    const clause = Math.max(window.lastIndexOf(';'), window.lastIndexOf(','));
    if (clause >= 32) return window.slice(0, clause).trim();
    const clipped = window.replace(/\s+\S*$/, '').trim();
    return `${clipped || window.trim()}…`;
  }

  constructor() {
    effect(() => {
      const question = this.params().get('q')?.trim() ?? '';
      const urlThreadId = this.params().get('thread');
      const shouldSend = this.params().get('pending') === '1';
      const forceDomain = this.params().get('forceDomain') ?? undefined;
      // A route with no thread means "start a new consultation". Never infer
      // continuity from component memory: Angular reuses this component when
      // Ask Home navigates here, which previously attached a fresh question
      // to whichever conversation happened to be open last.
      const threadId = urlThreadId;
      const key = `${threadId ?? ''}::${question}::${shouldSend}::${forceDomain ?? ''}`;
      if (key === this.lastRouteKey) return;

      if (shouldSend && question) {
        if (!threadId || threadId !== untracked(() => this.loadedThreadId)) {
          this.resetConversationState();
        }
        this.lastRouteKey = key;
        void this.startStream(question, threadId, forceDomain);
        return;
      }

      if (threadId && threadId !== untracked(() => this.loadedThreadId)) {
        this.resetConversationState();
        this.lastRouteKey = key;
        void this.loadThread(threadId);
        return;
      }

      this.lastRouteKey = key;

      if (!threadId && question && !untracked(() => this.messages()).length) {
        this.messages.set([
          this.toChatMessage({
            id: `local-user-${Date.now()}`,
            role: 'user',
            content: question,
            domain: null,
            refer_out_kind: null,
            evidence: null,
            created_at: null,
          }),
        ]);
      }
    });

    effect(() => {
      const profilesLoaded = this.kundlis.loaded();
      const profileId = this.kundlis.active()?.id ?? null;
      if (!profilesLoaded) return;

      // The first loaded profile establishes this view's scope. Every later
      // switch is a privacy boundary: immediately remove the old profile's
      // messages, cancel its stream, and return to a clean Ask Home.
      if (this.viewedProfileId === undefined) {
        this.viewedProfileId = profileId;
        return;
      }
      if (profileId === this.viewedProfileId) return;

      this.viewedProfileId = profileId;
      this.resetConversationState();
      this.lastRouteKey = null;
      void this.router.navigate(['/m', 'ask'], { replaceUrl: true });
    });
  }

  private resetConversationState(): void {
    this.abortController?.abort();
    this.abortController = null;
    this.threadLoadRevision += 1;
    this.activeThreadId.set(null);
    this.loadedThreadId = null;
    this.messages.set([]);
    this.selectedAssistant.set(null);
    this.streamedAnswer.set('');
    this.streamStatus.set(null);
    this.streamDomain.set(null);
    this.streamEvidence.set([]);
    this.streaming.set(false);
    this.loadingThread.set(false);
    this.submitError.set(null);
    this.whyOpen.set(false);
    this.listenOpen.set(false);
  }

  private async loadThread(threadId: string): Promise<boolean> {
    const requestRevision = ++this.threadLoadRevision;
    this.loadingThread.set(true);
    this.submitError.set(null);
    try {
      await this.kundlis.load();
      const requestedProfileId = this.kundlis.active()?.id ?? null;
      if (!requestedProfileId) {
        this.submitError.set('Select a profile before opening a conversation.');
        return false;
      }

      const detail = await this.threadsApi.get(threadId);
      if (requestRevision !== this.threadLoadRevision) return false;
      const currentProfileId = this.kundlis.active()?.id ?? null;
      if (
        currentProfileId !== requestedProfileId ||
        detail.thread.kundli_id !== requestedProfileId
      ) {
        // Never paint the fetched messages, even for one frame. The profile
        // may have changed while the request was in flight, or browser history
        // may contain a thread URL belonging to another profile.
        this.resetConversationState();
        this.lastRouteKey = null;
        await this.router.navigate(['/m', 'ask'], { replaceUrl: true });
        return false;
      }

      this.loadedThreadId = threadId;
      this.activeThreadId.set(threadId);
      const messages = detail.messages.map((message) => this.toChatMessage(message));
      this.messages.set(messages);
      const latestAssistant = [...messages].reverse().find((message) => message.role === 'assistant');
      this.selectedAssistant.set(latestAssistant ?? null);
      if (latestAssistant) {
        this.streamDomain.set(latestAssistant.domain);
        this.streamEvidence.set(latestAssistant.evidence);
        this.askState.rememberAnswer(threadId, latestAssistant.content);
      }
      return true;
    } catch (error) {
      if (requestRevision === this.threadLoadRevision) {
        this.submitError.set((error as Error).message);
      }
      return false;
    } finally {
      if (requestRevision === this.threadLoadRevision) {
        this.loadingThread.set(false);
      }
    }
  }

  private toChatMessage(message: MobileAskMessage): ChatMessage {
    const structured = this.readingFromEvidence(message.evidence);
    return {
      id: message.id,
      role: message.role,
      content: structured ? this.flattenReading(structured) : message.content,
      domain: message.domain,
      intent: null,
      status: this.statusFromPersistedMessage(message, structured),
      refer_out_kind: message.refer_out_kind,
      created_at: message.created_at,
      evidence: this.referencesFromEvidence(message.evidence),
      context_used: [],
      evidence_refs: [],
      profile_context_revision: this.numberFromEvidence(message.evidence, 'profile_context_revision'),
      profile_context_as_of: this.stringFromEvidence(message.evidence, 'profile_context_as_of'),
      reading: structured,
      options: this.clarificationOptionsFromEvidence(message.evidence),
    };
  }

  /** Reconstructs the terminal status a persisted assistant turn actually
   * had — reopening a thread from history must show the same "CLARIFY" /
   * "NOT READY" / "SAFETY" label the live turn showed, not a generic
   * "ANSWER" for everything just because `status` was never itself a
   * stored column. Mirrors exactly what ask_stream_routes.py's
   * `persist_turn` calls write into `evidence` for each terminal type. */
  private statusFromPersistedMessage(
    message: MobileAskMessage, structured: StructuredReading | null,
  ): string | null {
    if (message.role !== 'assistant') return null;
    if (structured) return 'answered';
    if (message.refer_out_kind) return 'refer_out';
    const evidence = message.evidence;
    if (evidence?.['clarification_options']) return 'clarification_needed';
    if (evidence?.['status'] === 'context_unavailable') return 'context_unavailable';
    if (evidence?.['status'] === 'domain_not_ready') return 'domain_not_ready';
    return null;
  }

  private clarificationOptionsFromEvidence(evidence: Record<string, unknown> | null | undefined): string[] {
    const value = evidence?.['clarification_options'] ?? evidence?.['available'];
    return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
  }

  private numberFromEvidence(
    evidence: Record<string, unknown> | null | undefined, key: string,
  ): number {
    const value = evidence?.[key];
    return typeof value === 'number' && Number.isFinite(value) ? value : 0;
  }

  private stringFromEvidence(
    evidence: Record<string, unknown> | null | undefined, key: string,
  ): string | null {
    const value = evidence?.[key];
    return typeof value === 'string' && value.trim() ? value : null;
  }

  protected profileContextLabel(message: ChatMessage): string | null {
    if (message.profile_context_revision <= 0) return null;
    const rawDate = message.profile_context_as_of;
    if (!rawDate) return 'Uses your saved profile context';
    const parsed = new Date(`${rawDate.slice(0, 10)}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) return 'Uses your saved profile context';
    const date = new Intl.DateTimeFormat(undefined, {
      day: 'numeric', month: 'short', year: 'numeric',
    }).format(parsed);
    return `Uses your saved profile context · ${date}`;
  }

  private readingFromEvidence(evidence: Record<string, unknown> | null | undefined): StructuredReading | null {
    const value = evidence?.['structured_reading'];
    if (!value || typeof value !== 'object') return null;
    const candidate = value as Partial<StructuredReading>;
    if (
      typeof candidate.acknowledgment !== 'string' ||
      typeof candidate.interpretation !== 'string' ||
      typeof candidate.summary_and_assurance !== 'string' ||
      !candidate.guidance ||
      typeof candidate.guidance !== 'object'
    ) {
      return null;
    }
    return {
      acknowledgment: candidate.acknowledgment,
      technical_basis: Array.isArray(candidate.technical_basis) ? candidate.technical_basis : [],
      interpretation: candidate.interpretation,
      summary_and_assurance: candidate.summary_and_assurance,
      guidance: {
        practical_actions: Array.isArray(candidate.guidance.practical_actions)
          ? candidate.guidance.practical_actions
          : [],
        remedies: Array.isArray(candidate.guidance.remedies) ? candidate.guidance.remedies : [],
        follow_up_questions: Array.isArray(candidate.guidance.follow_up_questions)
          ? candidate.guidance.follow_up_questions
          : [],
      },
      confidence: candidate.confidence ?? 'medium',
    };
  }

  private referencesFromEvidence(evidence: Record<string, unknown> | null | undefined): SourceReference[] {
    const value = evidence?.['references'];
    if (!Array.isArray(value)) return [];
    return value
      .map((item) => {
        if (!item || typeof item !== 'object') return null;
        const row = item as Partial<SourceReference>;
        return typeof row.statement === 'string' && typeof row.source_location === 'string'
          ? { statement: row.statement, source_location: row.source_location }
          : null;
      })
      .filter((item): item is SourceReference => item !== null);
  }

  private flattenReading(reading: StructuredReading): string {
    return [
      'Intent',
      reading.acknowledgment,
      'What this means',
      reading.interpretation,
      reading.summary_and_assurance,
      reading.guidance.practical_actions.length ? 'Next best steps' : '',
      ...reading.guidance.practical_actions,
      reading.guidance.remedies.length ? 'Traditional supports' : '',
      ...reading.guidance.remedies.map((remedy) => `${remedy.practice}: ${remedy.note}`),
    ].filter(Boolean).join('\n\n');
  }

  private async startStream(
    question: string, threadId: string | null, forceDomain?: string,
  ): Promise<void> {
    this.abortController?.abort();
    const controller = new AbortController();
    this.abortController = controller;
    await this.kundlis.load();
    if (controller.signal.aborted) {
      if (this.abortController === controller) this.abortController = null;
      return;
    }
    const profile = this.kundlis.active();
    if (!profile) {
      this.submitError.set('Select a profile before asking a question.');
      if (this.abortController === controller) this.abortController = null;
      return;
    }

    if (threadId) {
      if (this.loadedThreadId !== threadId) {
        const loaded = await this.loadThread(threadId);
        if (!loaded) {
          if (this.abortController === controller) this.abortController = null;
          return;
        }
      }
    }
    if (controller.signal.aborted || this.kundlis.active()?.id !== profile.id) {
      if (this.abortController === controller) this.abortController = null;
      return;
    }

    this.streaming.set(true);
    this.streamedAnswer.set('');
    this.streamStatus.set('Understanding your question…');
    this.streamDomain.set(null);
    this.streamEvidence.set([]);
    this.submitError.set(null);

    const userMessage = this.toChatMessage({
      id: `local-user-${Date.now()}`,
      role: 'user',
      content: question,
      domain: null,
      refer_out_kind: null,
      evidence: null,
      created_at: new Date().toISOString(),
    });
    const assistantId = `local-assistant-${Date.now()}`;
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: this.streamStatus() ?? 'Understanding your question…',
      domain: null,
      intent: null,
      status: 'understanding',
      refer_out_kind: null,
      created_at: null,
      evidence: [],
      context_used: [],
      evidence_refs: [],
      profile_context_revision: 0,
      profile_context_as_of: null,
      reading: null,
      options: [],
      streaming: true,
    };
    this.messages.update((items) => [...items, userMessage, assistantMessage]);
    this.selectedAssistant.set(assistantMessage);

    try {
      let finalThreadId: string | null = threadId;
      let referOutKind: string | null = null;
      for await (const event of this.askService.stream(profile.id, {
        question,
        thread_id: threadId ?? undefined,
        start_thread: !threadId,
        input_mode: 'text',
        domain_override: forceDomain,
      }, controller.signal)) {
        if (controller.signal.aborted || this.kundlis.active()?.id !== profile.id) {
          controller.abort();
          return;
        }
        if (this.isStatusEvent(event)) {
          this.streamStatus.set(event.label);
          this.updateAssistantMessage(assistantId, {
            content: event.label,
            status: event.stage,
            streaming: true,
          });
        } else if (this.isClarificationEvent(event)) {
          const message = event.message || [
            'I need one detail before I answer this properly.',
            event.options?.length ? `Try asking about ${event.options.join(' or ')}.` : '',
          ].filter(Boolean).join(' ');
          this.updateAssistantMessage(assistantId, {
            content: message,
            status: 'clarification_needed',
            intent: event.intent ?? null,
            options: event.options ?? [],
            streaming: false,
          });
          this.streaming.set(false);
        } else if (this.isDomainNotReadyEvent(event)) {
          const label = event.domain_label ?? event.domain ?? 'This specialist';
          const available = event.available?.length ? ` Try ${event.available.join(' or ')}.` : '';
          this.updateAssistantMessage(assistantId, {
            content: event.message || `${label} is not ready yet.${available}`,
            status: 'domain_not_ready',
            domain: event.domain ?? null,
            options: event.available ?? [],
            streaming: false,
          });
          this.streaming.set(false);
        } else if (this.isReferOutEvent(event)) {
          referOutKind = event.kind;
          this.updateAssistantMessage(assistantId, {
            content: event.answer,
            domain: event.kind,
            refer_out_kind: event.kind,
            status: 'refer_out',
            streaming: false,
          });
        } else if (this.isContextUnavailableEvent(event)) {
          finalThreadId = event.thread_id ?? finalThreadId;
          this.streamStatus.set(null);
          this.updateAssistantMessage(assistantId, {
            content: 'I could not check your saved profile context just now, so I am holding off rather than risk missing something you already shared. Please try again in a moment.',
            domain: event.domain ?? null,
            status: 'context_unavailable',
            streaming: false,
          });
          this.streaming.set(false);
        } else if (this.isFatalErrorEvent(event)) {
          finalThreadId = event.thread_id ?? finalThreadId;
          this.streamStatus.set(null);
          this.updateAssistantMessage(assistantId, {
            content: event.message || 'Siddha could not complete this answer cleanly. Please try again in a moment.',
            domain: event.domain ?? null,
            intent: event.intent ?? null,
            status: 'fatal_error',
            streaming: false,
          });
          this.streaming.set(false);
        } else if (this.isStructuredSuccessEvent(event)) {
          finalThreadId = event.thread_id ?? finalThreadId;
          this.streamDomain.set(event.domain);
          const references = event.reading.technical_basis.map((item) => ({
            statement: item.factor,
            source_location: this.sourceLabel(item.source),
          }));
          this.streamEvidence.set(references);
          const flattened = this.flattenReading(event.reading);
          this.streamedAnswer.set(flattened);
          this.updateAssistantMessage(assistantId, {
            content: flattened,
            domain: event.domain,
            intent: event.intent,
            status: event.status,
            evidence: references,
            context_used: event.context_used ?? [],
            evidence_refs: event.evidence_refs ?? [],
            profile_context_revision: event.profile_context_revision ?? 0,
            profile_context_as_of: event.profile_context_as_of ?? null,
            reading: event.reading,
            streaming: false,
          });
          if (finalThreadId) {
            this.activeThreadId.set(finalThreadId);
            const savedAt = new Date().toISOString();
            this.askState.rememberAnswer(finalThreadId, flattened);
            if (!threadId || finalThreadId !== threadId) {
              this.askState.rememberThread({
                id: finalThreadId,
                kundli_id: profile.id,
                title: question.slice(0, 80),
                message_count: 2,
                last_message_at: savedAt,
                created_at: savedAt,
              });
            }
          }
        } else if (this.isStructuredFailureEvent(event)) {
          finalThreadId = event.thread_id ?? finalThreadId;
          const status =
            event.status === 'generation_failed' ? 'generation_failed' : 'verification_failed';
          this.updateAssistantMessage(assistantId, {
            content: status === 'generation_failed'
              ? 'I could not reach the specialist cleanly enough to produce a grounded answer. Please try again in a moment.'
              : 'I could not produce an answer that passed Siddha\'s grounding checks. Please try again, or ask a narrower question.',
            domain: event.domain ?? null,
            intent: event.intent ?? null,
            status,
            context_used: event.context_used ?? [],
            evidence_refs: event.evidence_refs ?? [],
            streaming: false,
          });
          this.streaming.set(false);
        } else if ('delta' in event) {
          const next = event.reset ? event.delta : this.streamedAnswer() + event.delta;
          this.streamedAnswer.set(next);
          this.updateAssistantMessage(assistantId, { content: next, streaming: true });
        } else if ('done' in event) {
          finalThreadId = event.thread_id ?? finalThreadId;
          referOutKind = event.refer_out_kind;
          this.streamDomain.set(event.domain);
          this.streamEvidence.set(event.evidence);
          this.updateAssistantMessage(assistantId, {
            domain: event.domain,
            refer_out_kind: event.refer_out_kind,
            evidence: event.evidence,
            streaming: false,
          });
          if (finalThreadId) {
            this.activeThreadId.set(finalThreadId);
            const savedAt = new Date().toISOString();
            this.askState.rememberAnswer(finalThreadId, this.streamedAnswer());
            if (!threadId || finalThreadId !== threadId) {
              this.askState.rememberThread({
                id: finalThreadId,
                kundli_id: profile.id,
                title: question.slice(0, 80),
                message_count: 2,
                last_message_at: savedAt,
                created_at: savedAt,
              });
            }
          }
        }
      }

      if (controller.signal.aborted || this.kundlis.active()?.id !== profile.id) return;

      if (referOutKind && REFER_OUT_KINDS.has(referOutKind)) {
        await this.router.navigate(['/m', 'ask', 'refer'], {
          queryParams: { q: question, domain: referOutKind },
          replaceUrl: true,
        });
        return;
      }
      if (finalThreadId) {
        this.activeThreadId.set(finalThreadId);
        this.loadedThreadId = finalThreadId;
        this.lastRouteKey = `${finalThreadId}::::false`;
        await this.router.navigate(['/m', 'ask', 'answer'], {
          queryParams: { thread: finalThreadId },
          replaceUrl: true,
        });
      } else if (!this.streaming()) {
        await this.router.navigate(['/m', 'ask', 'answer'], {
          queryParams: { q: question },
          replaceUrl: true,
        });
      }
    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        this.updateAssistantMessage(assistantId, { streaming: false });
      } else {
        this.submitError.set((error as Error).message);
        this.updateAssistantMessage(assistantId, { streaming: false });
      }
    } finally {
      if (this.abortController === controller) {
        this.streaming.set(false);
        this.abortController = null;
      }
    }
  }

  private updateAssistantMessage(id: string, patch: Partial<ChatMessage>): void {
    this.messages.update((items) =>
      items.map((message) => (message.id === id ? { ...message, ...patch } : message)),
    );
    const updated = this.messages().find((message) => message.id === id);
    if (updated) this.selectedAssistant.set(updated);
  }

  private isStatusEvent(event: AskStreamEvent): event is Extract<AskStreamEvent, { type: 'status' }> {
    return 'type' in event && event.type === 'status';
  }

  private isClarificationEvent(
    event: AskStreamEvent,
  ): event is Extract<AskStreamEvent, { type: 'clarification_needed' }> {
    return 'type' in event && event.type === 'clarification_needed';
  }

  private isDomainNotReadyEvent(
    event: AskStreamEvent,
  ): event is Extract<AskStreamEvent, { type: 'domain_not_ready' }> {
    return 'type' in event && event.type === 'domain_not_ready';
  }

  private isReferOutEvent(event: AskStreamEvent): event is Extract<AskStreamEvent, { type: 'refer_out' }> {
    return 'type' in event && event.type === 'refer_out';
  }

  private isContextUnavailableEvent(
    event: AskStreamEvent,
  ): event is Extract<AskStreamEvent, { type: 'context_unavailable' }> {
    return 'type' in event && event.type === 'context_unavailable';
  }

  private isFatalErrorEvent(event: AskStreamEvent): event is Extract<AskStreamEvent, { type: 'fatal_error' }> {
    return 'type' in event && event.type === 'fatal_error';
  }

  private isStructuredSuccessEvent(
    event: AskStreamEvent,
  ): event is Extract<AskStreamEvent, { type: 'done'; status: 'answered' }> {
    return 'type' in event && event.type === 'done' && event.status === 'answered' && 'reading' in event;
  }

  private isStructuredFailureEvent(
    event: AskStreamEvent,
  ): event is Extract<AskStreamEvent, { type: 'done' }> {
    return 'type' in event && event.type === 'done' && event.status !== 'answered';
  }

  protected stopStreaming(): void {
    this.abortController?.abort();
    this.abortController = null;
    this.streaming.set(false);
    this.messages.update((items) =>
      items.map((message) =>
        message.streaming ? { ...message, streaming: false } : message,
      ),
    );
  }

  protected selectAssistant(message: ChatMessage): void {
    this.selectedAssistant.set(message);
  }

  protected answerLabel(message: ChatMessage): string {
    switch (message.status) {
      case 'domain_not_ready':
        return 'NOT READY';
      case 'clarification_needed':
        return 'CLARIFY';
      case 'refer_out':
        return 'SAFETY';
      case 'verification_failed':
      case 'generation_failed':
      case 'fatal_error':
        return 'GROUNDING';
      case 'context_unavailable':
        return 'CONTEXT';
      case 'answered':
        return 'ANSWER';
      default:
        return message.streaming ? 'WORKING' : 'ANSWER';
    }
  }

  protected answerTone(message: ChatMessage): VerdictTone {
    switch (message.status) {
      case 'answered':
        return 'good';
      case 'refer_out':
      case 'verification_failed':
      case 'generation_failed':
      case 'fatal_error':
        return 'bad';
      case 'context_unavailable':
        return 'warn';
      default:
        return 'warn';
    }
  }

  protected async copyAnswer(message: ChatMessage): Promise<void> {
    if (typeof navigator === 'undefined' || !navigator.clipboard) return;
    await navigator.clipboard.writeText(this.normaliseAnswerText(message.content));
  }

  protected editQuestion(message: ChatMessage): void {
    this.draft.set(message.content);
  }

  protected async archiveThread(): Promise<void> {
    const threadId = this.activeThreadId() ?? this.params().get('thread');
    if (!threadId || this.archivingThread()) return;
    this.archivingThread.set(true);
    this.submitError.set(null);
    try {
      await this.threadsApi.archive(threadId);
      await this.router.navigate(['/m', 'ask']);
    } catch (error) {
      this.submitError.set((error as Error).message);
    } finally {
      this.archivingThread.set(false);
    }
  }

  /**
   * Hands the verdict to the OS share sheet where available. No fallback UI:
   * on a platform without it, doing nothing is better than inventing a
   * share dialog the design never specified.
   */
  protected async share(): Promise<void> {
    const v = this.view();
    const message = this.selectedAssistant() ?? this.latestAssistant();
    if (typeof navigator !== 'undefined' && 'share' in navigator) {
      try {
        await navigator.share({ title: v.question, text: `${message?.content ?? v.verdict}\n\n${v.whatToDo}` });
      } catch {
        // Cancelled by the reader; nothing to report.
      }
    }
  }

  /** `option` is an explicit reader choice (a clarification chip), not new
   * question text — it travels as `forceDomain` so the orchestrator can
   * bypass keyword routing entirely (see AskOrchestrator.route()'s
   * `domain_override`). Previously this wrapped the original question in
   * "Answer this as a {label} question: …" and resent it through the
   * normal fuzzy router — since the router only checks whether a keyword
   * is *present*, not how many times, that added no disambiguating signal
   * and the same clarification fired again on every click, compounding the
   * prefix indefinitely. Uses the thread's original question (`firstUser`),
   * not `latestUser`, since a resend used to drift the "latest" question
   * with each wrapped attempt. */
  protected async askClarification(option: string): Promise<void> {
    const original = this.firstUser()?.content ?? this.params().get('q') ?? '';
    if (!original || this.streaming()) return;
    this.draft.set('');
    const threadId = this.activeThreadId() ?? this.params().get('thread') ?? undefined;
    await this.router.navigate(['/m', 'ask', 'answer'], {
      queryParams: { q: original, thread: threadId, pending: '1', forceDomain: option },
    });
  }

  /** Navigates to this same route with a new question — the constructor's
   * effect is what actually calls the orchestrator once params land. */
  protected async askAgain(question: string): Promise<void> {
    const q = question.trim();
    if (!q || this.streaming()) return;
    this.draft.set('');
    const threadId = this.activeThreadId() ?? this.params().get('thread') ?? undefined;
    await this.router.navigate(['/m', 'ask', 'answer'], {
      queryParams: { q, thread: threadId, pending: '1' },
    });
  }
}
