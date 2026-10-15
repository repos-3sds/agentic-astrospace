import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { EntitlementService } from '../../../core/entitlement.service';
import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';
import { SpeechService } from '../../../core/speech.service';
import { VedicService } from '../../../core/vedic.service';
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
        { provide: KundliStore, useValue: { loaded: signal(true), load: () => Promise.resolve(), active: signal({ name: 'Mine' }), activeId: signal(null) } },
        { provide: EntitlementService, useValue: { refresh: () => Promise.resolve(), askAllowance: signal(null), current: signal(null) } },
        { provide: VedicService, useValue: { dailyGuidance: () => Promise.resolve(null) } },
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
