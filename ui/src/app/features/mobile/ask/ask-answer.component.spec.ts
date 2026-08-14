import { computed, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { BehaviorSubject, of } from 'rxjs';

import { AskAnswerComponent } from './ask-answer.component';
import { PreferencesService, ExperienceMode } from '../../../core/preferences.service';
import { StructuredReading } from '../../../core/models';
import { AskService } from '../../../core/ask.service';
import { KundliStore } from '../../../core/kundli.store';
import { ProfileContextFact, ProfileContextService } from '../../../core/profile-context.service';
import { MobileAskStateService } from './mobile-ask-state.service';
import { MobileAskThreadService } from './mobile-ask-thread.service';

/**
 * 2026-08-10 (independent review, persona-depth/timing-precision task):
 * before this file there was NO spec at all for ask-answer.component,
 * meaning the persona-mode content-parity fix in this same commit series
 * (Guided/Balanced/Practitioner must render the complete explanation the
 * persona-aware agent returned, while differing in technical_basis disclosure)
 * had no automated guard. A future edit could reintroduce Guided-only
 * truncation (the actual historical bug this series fixed:
 * `guidedBody()`'s 190-char `compactSentence` clip, `guidedActions()`'s
 * `.slice(0,2)`) and nothing would catch it before a live screenshot pass.
 *
 * This constructs the real component via TestBed.runInInjectionContext
 * rather than a full fixture/template render — ActivatedRoute is faked
 * with empty query params (the constructor's `effect()` needs a
 * synchronous queryParamMap for `toSignal(..., { requireSync: true })`,
 * and empty params take the component's no-op branch, never touching the
 * network), Router is faked since nothing here navigates, and every other
 * injected service is the real `providedIn: 'root'` implementation — none
 * of them do eager HTTP/async work in their constructors, only `effect()`s
 * that write to localStorage/sessionStorage, which the test browser has.
 * The interpretation/summary_and_assurance/actions/remedies fields
 * themselves are unprocessed template reads (`{{ reading.interpretation
 * }}`, `@for (remedy of reading.guidance.remedies; ...)` etc, per
 * ask-answer.component.html) — there is no per-mode branch to regress on
 * those specifically, so this file focuses on the methods that DO branch
 * by mode, which is where the historical bug actually lived and where a
 * future regression is actually possible: readingActions(), technicalBasis(),
 * showTechnicalBasis(), guidedTechnicalHint().
 */
function createComponent(): AskAnswerComponent {
  TestBed.configureTestingModule({
    providers: [
      provideHttpClient(),
      provideHttpClientTesting(),
      { provide: ActivatedRoute, useValue: { queryParamMap: of(convertToParamMap({})) } },
      { provide: Router, useValue: { navigate: () => Promise.resolve(true) } },
    ],
  });
  return TestBed.runInInjectionContext(() => new AskAnswerComponent());
}

function setMode(component: AskAnswerComponent, mode: ExperienceMode): void {
  TestBed.inject(PreferencesService).experienceMode.set(mode);
}

const FULL_READING: StructuredReading = {
  acknowledgment: 'You asked whether now is a good time to change jobs.',
  technical_basis: [
    { factor: '10th lord Mars in Scorpio', reading: 'A strong Ruchaka Yoga for career authority.', source: 'houses' },
    { factor: 'Rahu mahadasha', reading: 'A restless, opportunity-seeking major period.', source: 'dasha_relevance' },
    { factor: 'Jupiter antardasha', reading: 'Activates the 2nd/11th houses of income.', source: 'dasha_relevance' },
    { factor: 'Ashtama Shani transit', reading: 'Saturn is 8th from natal Moon, a caution window.', source: 'gochara' },
    { factor: 'D10 Mars placement', reading: 'Own-sign strength in the career divisional chart.', source: 'vargas' },
  ],
  interpretation: 'Your chart holds real career strength, but the current transit favours patience over an immediate leap.',
  summary_and_assurance: 'The pressure you feel now is temporary; a clearer window opens once the transit passes.',
  guidance: {
    practical_actions: [
      'Avoid impulsive resignations until a new offer is signed.',
      'Use the next few months to quietly upgrade your skills.',
      'Vet any new employer for stability before committing.',
      'Revisit this question after the transit window closes.',
    ],
    remedies: [
      { practice: 'Engage in selfless service on Saturdays.', note: 'Traditionally eases Saturn-related pressure.' },
      { practice: 'Light a sesame-oil lamp on Saturday evenings.', note: 'A classical practice for grounding energy.' },
    ],
    follow_up_questions: ['Which month is strongest for this?', 'What chart factors support this?'],
  },
  confidence: 'high',
};

function messageWithReading(reading: StructuredReading | null): any {
  return {
    id: 'm1', role: 'assistant', content: '', domain: 'career', intent: null,
    status: 'answered', refer_out_kind: null, created_at: null,
    evidence: [], context_used: [], evidence_refs: [], reading, options: [],
    profile_context_revision: 0, profile_context_as_of: null,
  };
}

describe('AskAnswerComponent profile context provenance', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('formats the frozen ledger date only when saved context was used', () => {
    const component = createComponent();
    const withoutContext = messageWithReading(FULL_READING);
    expect((component as any).profileContextLabel(withoutContext)).toBeNull();

    const withContext = {
      ...withoutContext,
      profile_context_revision: 3,
      profile_context_as_of: '2026-08-14',
    };
    const label = (component as any).profileContextLabel(withContext);
    expect(label).toContain('Uses your saved profile context');
    expect(label).toContain('2026');
  });

  it('restores frozen ledger provenance from persisted history evidence', () => {
    const component = createComponent();
    const message = (component as any).toChatMessage({
      id: 'saved-1', role: 'assistant', content: 'Saved answer', domain: 'career',
      refer_out_kind: null, created_at: '2026-08-14T01:00:00Z',
      evidence: {
        structured_reading: FULL_READING,
        profile_context_revision: 4,
        profile_context_as_of: '2026-08-13',
      },
    });
    expect(message.profile_context_revision).toBe(4);
    expect(message.profile_context_as_of).toBe('2026-08-13');
  });

  it('restores a context-unavailable terminal message as a warning, not an answer', () => {
    const component = createComponent();
    const message = (component as any).toChatMessage({
      id: 'saved-context-error', role: 'assistant', content: 'Please try again.',
      domain: 'career', refer_out_kind: null, created_at: '2026-08-14T01:00:00Z',
      evidence: { status: 'context_unavailable', retryable: true },
    });
    expect(message.status).toBe('context_unavailable');
    expect((component as any).answerLabel(message)).toBe('CONTEXT');
    expect((component as any).answerTone(message)).toBe('warn');
  });

  it('recognises the live context-unavailable SSE envelope', () => {
    const component = createComponent();
    expect((component as any).isContextUnavailableEvent({
      type: 'context_unavailable', domain: 'career', retryable: true, thread_id: 't1',
    })).toBeTrue();
  });
});

describe('AskAnswerComponent persona-mode content parity', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('readingActions() returns the FULL, unsliced practical_actions list — mode-independent', () => {
    const component = createComponent();
    const actions = (component as any).readingActions(FULL_READING);
    expect(actions.length).toBe(FULL_READING.guidance.practical_actions.length);
    expect(actions).toEqual(FULL_READING.guidance.practical_actions);
  });

  it('readingActions() falls back to full follow_up_questions when there are no practical_actions', () => {
    const component = createComponent();
    const reading: StructuredReading = {
      ...FULL_READING,
      guidance: { ...FULL_READING.guidance, practical_actions: [] },
    };
    const actions = (component as any).readingActions(reading);
    expect(actions.length).toBe(reading.guidance.follow_up_questions.length);
    expect(actions[0]).toBe(`Ask next: ${reading.guidance.follow_up_questions[0]}`);
  });

  it('varies technical_basis disclosure by mode: none/1-line, subset, full', () => {
    const component = createComponent();
    const message = messageWithReading(FULL_READING);
    const totalFactors = FULL_READING.technical_basis.length;

    setMode(component, 'guided');
    expect((component as any).showTechnicalBasis(message)).toBe(false);
    const hint = (component as any).guidedTechnicalHint(message);
    expect(hint).toContain(FULL_READING.technical_basis[0].factor);
    // Guided's hint is a single compacted line, never the full granular list.
    expect(hint.length).toBeLessThan(150);

    setMode(component, 'balanced');
    expect((component as any).showTechnicalBasis(message)).toBe(true);
    const balancedItems = (component as any).technicalBasis(message);
    expect(balancedItems.length).toBeLessThan(totalFactors);
    expect(balancedItems.length).toBeGreaterThan(0);

    setMode(component, 'practitioner');
    expect((component as any).showTechnicalBasis(message)).toBe(true);
    const practitionerItems = (component as any).technicalBasis(message);
    expect(practitionerItems.length).toBe(totalFactors);
    expect(practitionerItems).toEqual(FULL_READING.technical_basis);

    // The actual regression this guards: practitioner's disclosure must be
    // strictly the largest of the three, balanced strictly in between.
    expect(practitionerItems.length).toBeGreaterThan(balancedItems.length);
  });

  it('guidedTechnicalHint() returns null when the reading has no technical_basis at all', () => {
    const component = createComponent();
    const reading: StructuredReading = { ...FULL_READING, technical_basis: [] };
    const hint = (component as any).guidedTechnicalHint(messageWithReading(reading));
    expect(hint).toBeNull();
  });

  it('readingActions() and technicalBasis() are unaffected by experience mode changes to the same reading object', () => {
    // Pins the actual product spec in one assertion: switching modes must
    // never change how much of the EXPLANATION (actions) is shown, only how
    // much TECHNICAL disclosure is shown.
    const component = createComponent();
    const guidedActions = (component as any).readingActions(FULL_READING);
    setMode(component, 'balanced');
    const balancedActions = (component as any).readingActions(FULL_READING);
    setMode(component, 'practitioner');
    const practitionerActions = (component as any).readingActions(FULL_READING);

    expect(guidedActions).toEqual(balancedActions);
    expect(balancedActions).toEqual(practitionerActions);
    expect(guidedActions).toEqual(FULL_READING.guidance.practical_actions);
  });

  // ── Readability of a long reading ──────────────────────────────────────
  // Both pinned from the shipped Android app (2026-08-11), where a genuinely
  // good ~900-word career reading was unreadable: the verdict clipped
  // mid-preposition and the body arrived as one unbroken slab. Copying the
  // answer read far better than looking at it, because the clipboard kept
  // the structure the page was throwing away.

  it('renders the interpretation as real paragraphs, not one slab', () => {
    const component = createComponent();
    const reading = { ...FULL_READING,
      interpretation: 'First about Saturn.\n\nSecond about Mercury.\n\nThird about timing.' };
    const paragraphs = (component as any).readingParagraphs(reading);
    expect(paragraphs.length).toBe(3);
    expect(paragraphs[1]).toBe('Second about Mercury.');
  });

  it('collapses incidental single newlines inside a paragraph', () => {
    const component = createComponent();
    const reading = { ...FULL_READING,
      interpretation: 'A sentence the model\nwrapped mid-line.\n\nA second paragraph.' };
    const paragraphs = (component as any).readingParagraphs(reading);
    expect(paragraphs.length).toBe(2);
    expect(paragraphs[0]).toBe('A sentence the model wrapped mid-line.');
  });

  it('does not clip the verdict mid-phrase', () => {
    const component = createComponent();
    // The exact sentence the shipped app rendered as
    // "...it is engineered for enduring..." — stopping on a preposition.
    const message: any = { reading: { ...FULL_READING, summary_and_assurance:
      'Your chart is not built for fleeting, superficial success; it is engineered for enduring professional respect and mastery.' } };
    const headline = (component as any).answerHeadline(message);
    expect(headline.endsWith('enduring…')).toBeFalse();
    expect(headline).toContain('superficial success');
  });

  it('clips an over-long verdict at a clause boundary, not a preposition', () => {
    const component = createComponent();
    const message: any = { reading: { ...FULL_READING, summary_and_assurance:
      'A very long opening clause that runs well past any sensible headline budget indeed, and then continues onward with a great deal more text that should not appear at all.' } };
    const headline = (component as any).answerHeadline(message);
    expect(headline.endsWith('indeed')).toBeTrue();
  });
});

interface AskIsolationHarness {
  component: AskAnswerComponent;
  params: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  activeId: ReturnType<typeof signal<string | null>>;
  router: { navigate: jasmine.Spy };
  threads: { get: jasmine.Spy };
  ask: { stream: jasmine.Spy };
  askState: { answer: jasmine.Spy; rememberAnswer: jasmine.Spy; rememberThread: jasmine.Spy };
}

function threadDetail(threadId: string, kundliId: string) {
  return {
    thread: {
      id: threadId,
      kundli_id: kundliId,
      title: `${kundliId} private question`,
      message_count: 2,
      last_message_at: '2026-08-11T00:00:00Z',
      created_at: '2026-08-11T00:00:00Z',
    },
    messages: [
      {
        id: `${threadId}-user`, role: 'user' as const,
        content: `${kundliId} private question`, domain: null,
        refer_out_kind: null, evidence: null, created_at: null,
      },
      {
        id: `${threadId}-assistant`, role: 'assistant' as const,
        content: `${kundliId} private answer`, domain: 'career',
        refer_out_kind: null, evidence: null, created_at: null,
      },
    ],
  };
}

function createIsolationHarness(
  initialParams: Record<string, string>,
  activeProfileId = 'profile-a',
): AskIsolationHarness {
  const params = new BehaviorSubject(convertToParamMap(initialParams));
  const activeId = signal<string | null>(activeProfileId);
  const profiles = [
    { id: 'profile-a', name: 'Profile A' },
    { id: 'profile-b', name: 'Profile B' },
  ];
  const store = {
    loaded: signal(true),
    activeId,
    active: computed(() => profiles.find((profile) => profile.id === activeId()) ?? null),
    load: jasmine.createSpy().and.resolveTo(undefined),
  };
  const router = { navigate: jasmine.createSpy().and.resolveTo(true) };
  const threads = {
    get: jasmine.createSpy().and.callFake((threadId: string) =>
      Promise.resolve(threadDetail(threadId, 'profile-a'))),
    archive: jasmine.createSpy().and.resolveTo(undefined),
  };
  const ask = {
    stream: jasmine.createSpy().and.callFake(async function* () { return; }),
  };
  const askState = {
    answer: jasmine.createSpy().and.returnValue(null),
    rememberAnswer: jasmine.createSpy(),
    rememberThread: jasmine.createSpy(),
  };

  TestBed.configureTestingModule({
    providers: [
      provideHttpClient(),
      provideHttpClientTesting(),
      { provide: ActivatedRoute, useValue: { queryParamMap: params } },
      { provide: Router, useValue: router },
      { provide: KundliStore, useValue: store },
      { provide: MobileAskThreadService, useValue: threads },
      { provide: AskService, useValue: ask },
      { provide: MobileAskStateService, useValue: askState },
    ],
  });
  const component = TestBed.runInInjectionContext(() => new AskAnswerComponent());
  TestBed.flushEffects();
  return { component, params, activeId, router, threads, ask, askState };
}

async function settleEffects(): Promise<void> {
  TestBed.flushEffects();
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}

describe('AskAnswerComponent profile isolation and thread lifecycle', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('starts an Ask Home submission as a new thread even when this component cached an old thread', async () => {
    const harness = createIsolationHarness({ thread: 'thread-a' });
    await settleEffects();
    expect((harness.component as any).activeThreadId()).toBe('thread-a');

    const startStream = spyOn(harness.component as any, 'startStream').and.resolveTo(undefined);
    harness.params.next(convertToParamMap({ q: 'A genuinely new question', pending: '1' }));
    await settleEffects();

    expect(startStream).toHaveBeenCalledOnceWith('A genuinely new question', null, undefined);
    expect((harness.component as any).activeThreadId()).toBeNull();
    expect((harness.component as any).messages()).toEqual([]);
  });

  it('never paints a thread fetched for profile A after the reader switches to profile B', async () => {
    let resolveThread!: (value: ReturnType<typeof threadDetail>) => void;
    const pendingThread = new Promise<ReturnType<typeof threadDetail>>((resolve) => {
      resolveThread = resolve;
    });
    const harness = createIsolationHarness({});
    harness.threads.get.and.returnValue(pendingThread);
    harness.params.next(convertToParamMap({ thread: 'thread-a' }));
    await settleEffects();
    (harness.component as any).view();
    expect(harness.askState.answer).not.toHaveBeenCalledWith('thread-a');

    harness.activeId.set('profile-b');
    await settleEffects();
    resolveThread(threadDetail('thread-a', 'profile-a'));
    await settleEffects();

    expect((harness.component as any).messages()).toEqual([]);
    expect((harness.component as any).activeThreadId()).toBeNull();
    expect(harness.router.navigate).toHaveBeenCalledWith(['/m', 'ask'], { replaceUrl: true });
  });

  it('rejects a browser-history thread belonging to another active profile before rendering it', async () => {
    const harness = createIsolationHarness({ thread: 'thread-a' }, 'profile-b');
    await settleEffects();

    expect(harness.threads.get).toHaveBeenCalledWith('thread-a');
    expect((harness.component as any).messages()).toEqual([]);
    expect((harness.component as any).activeThreadId()).toBeNull();
    expect(harness.router.navigate).toHaveBeenCalledWith(['/m', 'ask'], { replaceUrl: true });
  });

  it('ignores a stale thread response after the reader opens a newer thread', async () => {
    const resolvers = new Map<string, (value: ReturnType<typeof threadDetail>) => void>();
    const harness = createIsolationHarness({});
    harness.threads.get.and.callFake((threadId: string) =>
      new Promise<ReturnType<typeof threadDetail>>((resolve) => resolvers.set(threadId, resolve)));

    harness.params.next(convertToParamMap({ thread: 'thread-a' }));
    await settleEffects();
    harness.params.next(convertToParamMap({ thread: 'thread-b' }));
    await settleEffects();

    resolvers.get('thread-b')?.(threadDetail('thread-b', 'profile-a'));
    await settleEffects();
    expect((harness.component as any).activeThreadId()).toBe('thread-b');

    resolvers.get('thread-a')?.(threadDetail('thread-a', 'profile-a'));
    await settleEffects();
    expect((harness.component as any).activeThreadId()).toBe('thread-b');
    expect((harness.component as any).messages()[0].id).toBe('thread-b-user');
  });

  it('drops late stream events from profile A after switching to profile B', async () => {
    let continueStream!: () => void;
    const gate = new Promise<void>((resolve) => { continueStream = resolve; });
    const harness = createIsolationHarness({});
    harness.ask.stream.and.callFake(async function* () {
      yield { type: 'status', stage: 'interpreting', label: 'Interpreting profile A…' };
      await gate;
      // Deliberately ignore AbortSignal to model a late transport frame.
      yield { type: 'delta', delta: 'PROFILE A PRIVATE ANSWER' };
    });
    harness.params.next(convertToParamMap({ q: 'Profile A question', pending: '1' }));
    await settleEffects();

    harness.activeId.set('profile-b');
    await settleEffects();
    continueStream();
    await settleEffects();

    expect((harness.component as any).messages()).toEqual([]);
    expect((harness.component as any).streamedAnswer()).toBe('');
    expect(harness.router.navigate).toHaveBeenCalledWith(['/m', 'ask'], { replaceUrl: true });
  });

  it('does not submit when profile switching and a pending route race in the same turn', async () => {
    const harness = createIsolationHarness({});
    await settleEffects();

    harness.activeId.set('profile-b');
    harness.params.next(convertToParamMap({ q: 'Question from the stale profile view', pending: '1' }));
    await settleEffects();

    expect(harness.ask.stream).not.toHaveBeenCalled();
    expect((harness.component as any).messages()).toEqual([]);
    expect(harness.router.navigate).toHaveBeenCalledWith(['/m', 'ask'], { replaceUrl: true });
  });
});

describe('AskAnswerComponent memory undo', () => {
  afterEach(() => TestBed.resetTestingModule());

  function fact(overrides: Partial<ProfileContextFact> = {}): ProfileContextFact {
    return {
      id: 'fact-new', ref: 'profile_fact:fact-new@1', category: 'life_stage',
      key: 'employment_status', value: { code: 'retired' },
      valid_from: null, valid_to: null, status: 'active', sensitivity: 'personal',
      source: { kind: 'reader_statement', channel: 'ask' }, revision: 2,
      supersedes_id: null, ...overrides,
    };
  }

  it('undoes via undo-supersede, not plain delete, when the saved fact replaced an earlier value', async () => {
    const harness = createIsolationHarness({});
    await settleEffects();
    const profileContext = TestBed.inject(ProfileContextService);
    const undoSupersede = spyOn(profileContext, 'undoSupersede').and.resolveTo({
      revision: 3, removed_fact_id: 'fact-new', restored_fact: fact({ id: 'fact-old', status: 'active' }),
    });
    const remove = spyOn(profileContext, 'remove').and.resolveTo({ revision: 3, fact_id: 'fact-new', status: 'deleted' });

    (harness.component as any).memorySaved.set({
      profileId: 'profile-a', revision: 2,
      fact: fact({ supersedes_id: 'fact-old' }),
      message: 'Remembered work status for this profile.',
    });
    await (harness.component as any).undoMemory();

    expect(undoSupersede).toHaveBeenCalledOnceWith('profile-a', 'fact-new', 2);
    expect(remove).not.toHaveBeenCalled();
    expect((harness.component as any).memorySaved()).toBeNull();
  });

  it('undoes via plain delete when the saved fact was a brand-new value, not a replacement', async () => {
    const harness = createIsolationHarness({});
    await settleEffects();
    const profileContext = TestBed.inject(ProfileContextService);
    const undoSupersede = spyOn(profileContext, 'undoSupersede').and.resolveTo({} as never);
    const remove = spyOn(profileContext, 'remove').and.resolveTo({ revision: 2, fact_id: 'fact-new', status: 'deleted' });

    (harness.component as any).memorySaved.set({
      profileId: 'profile-a', revision: 1,
      fact: fact({ supersedes_id: null }),
      message: 'Remembered work status for this profile.',
    });
    await (harness.component as any).undoMemory();

    expect(remove).toHaveBeenCalledOnceWith('profile-a', 'fact-new', 1);
    expect(undoSupersede).not.toHaveBeenCalled();
    expect((harness.component as any).memorySaved()).toBeNull();
  });
});
