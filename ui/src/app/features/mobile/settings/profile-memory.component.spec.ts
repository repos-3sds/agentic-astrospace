import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';
import {
  ProfileContextFact,
  ProfileContextProjection,
  ProfileContextService,
} from '../../../core/profile-context.service';
import { ProfileMemoryComponent } from './profile-memory.component';

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

function projection(profileId: string, facts: ProfileContextFact[] = []): ProfileContextProjection {
  return {
    profile_id: profileId,
    revision: facts.length + 1,
    as_of: '2026-08-14T00:00:00Z',
    status: 'ready',
    contradictions: [],
    facts,
    logical_constraints: [],
  };
}

function employmentFact(id: string, code: string): ProfileContextFact {
  return {
    id,
    ref: `profile_fact:${id}@1`,
    category: 'life_stage',
    key: 'employment_status',
    value: { code },
    valid_from: null,
    valid_to: null,
    status: 'active',
    sensitivity: 'personal',
    source: { kind: 'profile_form', channel: 'profile_settings' },
    revision: 1,
  };
}

describe('ProfileMemoryComponent', () => {
  let fixture: ComponentFixture<ProfileMemoryComponent>;
  let routeParams: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let context: jasmine.SpyObj<ProfileContextService>;

  beforeEach(async () => {
    routeParams = new BehaviorSubject(convertToParamMap({ id: 'profile-a' }));
    context = jasmine.createSpyObj<ProfileContextService>(
      'ProfileContextService',
      ['load', 'create', 'correct', 'remove', 'export'],
    );
    context.load.and.resolveTo(projection('profile-a'));

    await TestBed.configureTestingModule({
      imports: [ProfileMemoryComponent],
      providers: [
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { paramMap: routeParams.asObservable() } },
        { provide: ProfileContextService, useValue: context },
        {
          provide: PreferencesService,
          useValue: { memoryEnabled: signal(true), memoryMode: signal('ask') },
        },
        {
          provide: KundliStore,
          useValue: {
            kundlis: signal([
              { id: 'profile-a', name: 'Profile A' },
              { id: 'profile-b', name: 'Profile B' },
            ]),
            load: () => Promise.resolve(),
          },
        },
      ],
    }).compileComponents();

  });

  it('discards a late response from the previously routed profile', async () => {
    const oldRequest = deferred<ProfileContextProjection>();
    context.load.and.callFake((profileId) => profileId === 'profile-a'
      ? oldRequest.promise
      : Promise.resolve(projection('profile-b', [employmentFact('b-fact', 'retired')])));

    await createComponent();
    routeParams.next(convertToParamMap({ id: 'profile-b' }));
    await fixture.whenStable();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Profile B');
    expect(fixture.nativeElement.textContent).toContain('Retired');

    oldRequest.resolve(projection('profile-a', [employmentFact('a-fact', 'employed')]));
    await fixture.whenStable();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Profile B');
    expect(fixture.nativeElement.textContent).toContain('Retired');
    expect(fixture.nativeElement.textContent).not.toContain('Employed');
  });

  it('clears a previous profile busy state when the route changes', async () => {
    const saveRequest = deferred<{ revision: number; fact: ProfileContextFact }>();
    context.create.and.returnValue(saveRequest.promise);
    await createComponent();

    button('Add profile context').click();
    fixture.detectChanges();
    button('Save to this profile').click();
    fixture.detectChanges();
    expect(button('Export').disabled).toBeTrue();

    context.load.and.resolveTo(projection('profile-b'));
    routeParams.next(convertToParamMap({ id: 'profile-b' }));
    await fixture.whenStable();
    fixture.detectChanges();
    expect(button('Export').disabled).toBeFalse();

    saveRequest.resolve({ revision: 2, fact: employmentFact('a-fact', 'employed') });
    await fixture.whenStable();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Profile B');
    expect(fixture.nativeElement.textContent).not.toContain('Employed');
  });

  it('keeps the stale-revision explanation visible after refreshing', async () => {
    context.load.and.resolveTo(projection(
      'profile-a', [employmentFact('a-fact', 'employed')],
    ));
    await createComponent();
    context.correct.and.rejectWith(new Error('stale_revision'));

    button('Edit').click();
    fixture.detectChanges();
    button('Save to this profile').click();
    await fixture.whenStable();
    fixture.detectChanges();

    const alert = fixture.nativeElement.querySelector('[role="alert"]');
    expect(alert?.textContent).toContain('changed on another screen or device');
    expect(context.load).toHaveBeenCalledTimes(2);
  });

  it('requires an explicit second action before removing a fact', async () => {
    context.load.and.resolveTo(projection(
      'profile-a', [employmentFact('a-fact', 'retired')],
    ));
    await createComponent();

    button('Remove').click();
    fixture.detectChanges();
    expect(context.remove).not.toHaveBeenCalled();
    expect(fixture.nativeElement.textContent).toContain('Remove from future readings?');
    expect(button('Keep')).toBeTruthy();
  });

  function button(label: string): HTMLButtonElement {
    const match = [...fixture.nativeElement.querySelectorAll('button')]
      .find((candidate: HTMLButtonElement) => candidate.textContent?.trim() === label);
    if (!match) throw new Error(`Button not found: ${label}`);
    return match as HTMLButtonElement;
  }

  async function createComponent(): Promise<void> {
    fixture = TestBed.createComponent(ProfileMemoryComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }
});
