import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { EMPTY } from 'rxjs';
import { MobileAskThreadService } from '../../mobile/ask/mobile-ask-thread.service';
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
      { provide: Router, useValue: { events: EMPTY } },
      { provide: MobileAskThreadService, useValue: { list: jasmine.createSpy().and.resolveTo([]) } },
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

  it('keeps standalone workspace destinations outside the Kundli shell', () => {
    const activeId = signal<string | null>('profile-a');
    TestBed.configureTestingModule({ providers: [
      { provide: KundliStore, useValue: { activeId } },
      { provide: ActivatedRoute, useValue: { snapshot: { routeConfig: { path: 'ask/:id' } } } },
      { provide: ASK_NAVIGATION, useFactory: webAskNavigation },
    ] });
    const navigation = TestBed.inject(ASK_NAVIGATION);
    expect(navigation.path()).toEqual(['/ask', 'profile-a']);
    expect(navigation.path('answer')).toEqual(['/ask', 'profile-a', 'answer']);
    expect(navigation.path('memory')).toEqual(['/ask', 'profile-a', 'memory']);
    expect(navigation.chart()).toEqual(['/kundli', 'profile-a', 'chart']);
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

  it('discards outgoing-profile recent chats when a new profile wins the race', async () => {
    const store = setup();
    const component = TestBed.runInInjectionContext(() => new AskTabComponent());
    await Promise.resolve();
    await Promise.resolve();
    const list = TestBed.inject(MobileAskThreadService).list as jasmine.Spy;
    let finishOld!: (rows: any[]) => void;
    list.and.returnValue(new Promise(resolve => { finishOld = resolve; }));
    store.activeId.set('profile-a');
    const oldLoad = (component as any).loadRecent();
    store.activeId.set('profile-b');
    list.and.resolveTo([{ id: 'b-chat', kundli_id: 'profile-b', title: 'B' }]);
    await (component as any).loadRecent();
    finishOld([{ id: 'a-chat', kundli_id: 'profile-a', title: 'A' }]);
    await oldLoad;
    expect((component as any).recent().map((row: any) => row.id)).toEqual(['b-chat']);
  });
});
