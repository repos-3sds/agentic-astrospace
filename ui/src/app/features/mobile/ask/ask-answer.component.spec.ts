import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of } from 'rxjs';

import { AskAnswerComponent } from './ask-answer.component';
import { PreferencesService, ExperienceMode } from '../../../core/preferences.service';
import { StructuredReading } from '../../../core/models';

/**
 * 2026-08-10 (independent review, persona-depth/timing-precision task):
 * before this file there was NO spec at all for ask-answer.component,
 * meaning the persona-mode content-parity fix in this same commit series
 * (Guided/Balanced/Practitioner must render an IDENTICAL explanation —
 * interpretation, summary_and_assurance, guidance.practical_actions,
 * guidance.remedies — and differ ONLY on technical_basis disclosure depth)
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
  };
}

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

  it('technical_basis disclosure is the ONLY thing that varies by mode: none/1-line, subset, full', () => {
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
});
