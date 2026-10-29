import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { EntitlementService } from '../../../core/entitlement.service';
import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';
import { SpeechService } from '../../../core/speech.service';
import { VedicService } from '../../../core/vedic.service';
import { AskService } from '../../../core/ask.service';
import { AskHomeComponent } from './ask-home.component';

describe('AskHomeComponent ?q handoff', () => {
  let params: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let navigate: jasmine.Spy;

  beforeEach(() => {
    params = new BehaviorSubject(convertToParamMap({}));
    TestBed.configureTestingModule({
      imports: [AskHomeComponent],
      providers: [
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { queryParamMap: params.asObservable(), snapshot: { queryParamMap: convertToParamMap({}) } } },
        { provide: KundliStore, useValue: { loaded: signal(true), load: () => Promise.resolve(), active: signal({ name: 'Mine' }), owner: signal(null), activeId: signal(null) } },
        { provide: EntitlementService, useValue: { refresh: () => Promise.resolve(), askAllowance: signal(null), current: signal(null) } },
        { provide: VedicService, useValue: { dailyGuidance: () => Promise.resolve(null) } },
        { provide: AskService, useValue: { suggestions: () => Promise.resolve(null) } },
        { provide: SpeechService, useValue: { start: () => Promise.resolve(), stop: () => Promise.resolve(), transcript: signal(''), listening: signal(false) } },
        {
          provide: PreferencesService,
          useValue: { experienceMode: signal('balanced'), language: signal('en') },
        },
      ],
    });
    navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
  });

  it('fills the composer from every new ?q, not only the first visit, and clears it from the URL', () => {
    // The handoff lives in the constructor's subscription; the template (and
    // the services it renders from) is not what is under test.
    const fixture = TestBed.createComponent(AskHomeComponent);
    expect(fixture.componentInstance.draft()).toBe('');

    params.next(convertToParamMap({ q: 'Explain my week' }));
    expect(fixture.componentInstance.draft()).toBe('Explain my week');
    expect(navigate).toHaveBeenCalledWith([], jasmine.objectContaining({ queryParams: { q: null }, replaceUrl: true }));

    // The reader types; clearing the param must not wipe it.
    fixture.componentInstance.draft.set('My own words');
    params.next(convertToParamMap({}));
    expect(fixture.componentInstance.draft()).toBe('My own words');

    // The retained tab gets a second handoff.
    params.next(convertToParamMap({ q: 'Explain my month' }));
    expect(fixture.componentInstance.draft()).toBe('Explain my month');
  });
});

describe('AskHomeComponent topic chips', () => {
  const payload = {
    as_of: '2026-10-28',
    topics: [],
    general: [{ prompt: 'What does my Mercury sub-period bring for money and savings?', because: 'Mercury looks after your savings' }],
    by_topic: {
      work: [{ prompt: 'How is my Mars major period shaping my work?', because: 'Mars sits in your house of career' }],
      marriage: [{ prompt: 'How is my Mars major period shaping marriage and partnership?', because: 'Mars looks after your marriage' }],
    },
  };

  async function make(active: string | null) {
    TestBed.configureTestingModule({
      imports: [AskHomeComponent],
      providers: [
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { queryParamMap: new BehaviorSubject(convertToParamMap({})).asObservable(), snapshot: { queryParamMap: convertToParamMap({}) } } },
        { provide: KundliStore, useValue: { loaded: signal(true), load: () => Promise.resolve(), active: signal({ id: active, name: 'Mine' }), owner: signal(null), activeId: signal(active), profiles: signal([]) } },
        { provide: EntitlementService, useValue: { refresh: () => Promise.resolve(), askAllowance: signal(null), current: signal(null) } },
        { provide: VedicService, useValue: { dailyGuidance: () => Promise.resolve(null) } },
        { provide: AskService, useValue: { suggestions: () => Promise.resolve(payload) } },
        { provide: SpeechService, useValue: { start: () => Promise.resolve(), stop: () => Promise.resolve(), transcript: signal(''), listening: signal(false), supported: signal(false) } },
        { provide: PreferencesService, useValue: { experienceMode: signal('balanced'), language: signal('en') } },
      ],
    });
    const fixture = TestBed.createComponent(AskHomeComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    return fixture.componentInstance;
  }

  it('swaps the list for the tapped topic, and back when tapped again', async () => {
    const home = await make('k1');
    expect(home.suggestions()[0].prompt).toContain('money and savings');
    home['toggleTopic']('work');
    expect(home.suggestions().map((s) => s.prompt)).toEqual(['How is my Mars major period shaping my work?']);
    home['toggleTopic']('marriage');
    expect(home.suggestions()[0].prompt).toContain('marriage');
    home['toggleTopic']('marriage');
    expect(home.suggestions()[0].prompt).toContain('money and savings');
  });

  it('falls back to a neutral list for a topic the chart list has nothing for', async () => {
    const home = await make('k1');
    home['toggleTopic']('child');
    const prompts = home.suggestions().map((s) => s.prompt);
    expect(prompts.length).toBe(3);
    expect(prompts.every((p) => p.includes('children'))).toBeTrue();
    expect(prompts.some((p) => p.includes('my children'))).toBeFalse();
  });
});

describe('AskHomeComponent AI-sharing notice', () => {
  let navigate: jasmine.Spy;
  let agreed: ReturnType<typeof signal<boolean>>;

  beforeEach(() => {
    agreed = signal(false);
    TestBed.configureTestingModule({
      imports: [AskHomeComponent],
      providers: [
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { queryParamMap: new BehaviorSubject(convertToParamMap({})).asObservable(), snapshot: { queryParamMap: convertToParamMap({}) } } },
        { provide: KundliStore, useValue: { loaded: signal(true), load: () => Promise.resolve(), active: signal({ name: 'Mine' }), owner: signal(null), activeId: signal(null) } },
        { provide: EntitlementService, useValue: { refresh: () => Promise.resolve(), askAllowance: signal(null), current: signal(null) } },
        { provide: VedicService, useValue: { dailyGuidance: () => Promise.resolve(null) } },
        { provide: AskService, useValue: { suggestions: () => Promise.resolve(null) } },
        { provide: SpeechService, useValue: { start: () => Promise.resolve(), stop: () => Promise.resolve(), transcript: signal(''), listening: signal(false) } },
        { provide: PreferencesService, useValue: { experienceMode: signal('balanced'), language: signal('en'), aiSharingAgreed: agreed } },
      ],
    });
    navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
  });

  it('holds the first question until the reader agrees, then sends it', async () => {
    const home = TestBed.createComponent(AskHomeComponent).componentInstance;
    await home['ask']('Will my work settle?');
    expect(navigate).not.toHaveBeenCalled();
    expect(home['pendingQuestion']()).toBe('Will my work settle?');

    home['agreeToAiSharing']();
    await Promise.resolve();
    expect(agreed()).toBeTrue();
    expect(home['pendingQuestion']()).toBeNull();
    expect(navigate).toHaveBeenCalledWith(jasmine.anything(), jasmine.objectContaining({
      queryParams: jasmine.objectContaining({ q: 'Will my work settle?' }),
    }));
  });

  it('asks straight away once agreed', async () => {
    agreed.set(true);
    const home = TestBed.createComponent(AskHomeComponent).componentInstance;
    await home['ask']('Will my work settle?');
    expect(navigate).toHaveBeenCalled();
    expect(home['pendingQuestion']()).toBeNull();
  });
});
