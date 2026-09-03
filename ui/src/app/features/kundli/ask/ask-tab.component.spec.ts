import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { AskTabComponent, webAskNavigation } from './ask-tab.component';
import { ASK_NAVIGATION } from '../../mobile/ask/ask-navigation';
import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';

describe('Web Ask shared conversation host', () => {
  function setup() {
    const activeId = signal<string | null>('profile-a');
    const store = {
      activeId, kundlis: signal([{ id: 'profile-a' }, { id: 'profile-b' }]),
      load: jasmine.createSpy().and.resolveTo(),
      setActive: (id: string) => activeId.set(id),
    };
    TestBed.configureTestingModule({ providers: [
      { provide: KundliStore, useValue: store },
      { provide: PreferencesService, useValue: { experienceMode: signal('balanced') } },
      { provide: ActivatedRoute, useValue: { parent: { snapshot: { paramMap: convertToParamMap({ id: 'profile-b' }) } } } },
      { provide: ASK_NAVIGATION, useFactory: webAskNavigation },
    ] });
    return store;
  }

  it('keeps every conversation destination inside the current web profile', () => {
    const store = setup();
    const navigation = TestBed.inject(ASK_NAVIGATION);
    expect(navigation.path('answer')).toEqual(['/kundli', 'profile-a', 'ask', 'answer']);
    store.activeId.set('profile-b');
    expect(navigation.path('history')).toEqual(['/kundli', 'profile-b', 'ask', 'history']);
    expect(navigation.path('memory')).toEqual(['/kundli', 'profile-b', 'ask', 'memory']);
  });

  it('waits for profiles and binds direct entry to the URL, not the saved selection', async () => {
    const store = setup();
    const component = TestBed.runInInjectionContext(() => new AskTabComponent());
    expect((component as any).ready()).toBeFalse();
    await Promise.resolve();
    expect(store.activeId()).toBe('profile-b');
    expect((component as any).ready()).toBeTrue();
  });

  it('writes persona changes to the same preferences consumed by streamed Ask', () => {
    setup();
    const component = TestBed.runInInjectionContext(() => new AskTabComponent());
    (component as any).setMode('practitioner');
    expect(TestBed.inject(PreferencesService).experienceMode()).toBe('practitioner');
    (component as any).setMode('invalid');
    expect(TestBed.inject(PreferencesService).experienceMode()).toBe('practitioner');
  });
});
