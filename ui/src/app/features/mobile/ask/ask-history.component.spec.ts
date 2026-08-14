import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { AskHistoryComponent } from './ask-history.component';
import { MobileAskThread, MobileAskThreadService } from './mobile-ask-thread.service';

describe('AskHistoryComponent active and archived conversations', () => {
  const thread: MobileAskThread = {
    id: 'thread-1', kundli_id: 'profile-1', title: 'Career timing',
    message_count: 4, last_message_at: null, created_at: null,
  };

  let api: jasmine.SpyObj<MobileAskThreadService>;
  let router: jasmine.SpyObj<Router>;
  let component: AskHistoryComponent;

  beforeEach(async () => {
    api = jasmine.createSpyObj<MobileAskThreadService>('MobileAskThreadService', [
      'list', 'get', 'archive', 'restore', 'delete',
    ]);
    api.list.and.resolveTo([thread]);
    api.archive.and.resolveTo(undefined);
    api.restore.and.resolveTo(undefined);
    api.delete.and.resolveTo(undefined);
    router = jasmine.createSpyObj<Router>('Router', ['navigate']);
    router.navigate.and.resolveTo(true);
    TestBed.configureTestingModule({
      providers: [
        { provide: MobileAskThreadService, useValue: api },
        { provide: Router, useValue: router },
        {
          provide: KundliStore,
          useValue: {
            load: jasmine.createSpy().and.resolveTo(undefined),
            active: signal({ id: 'profile-1' }),
          },
        },
      ],
    });
    component = TestBed.runInInjectionContext(() => new AskHistoryComponent());
    await Promise.resolve();
    await Promise.resolve();
  });

  afterEach(() => TestBed.resetTestingModule());

  it('loads archived threads separately and opens one without restoring it implicitly', async () => {
    (component as any).switchView('archived');
    await Promise.resolve();
    await Promise.resolve();
    expect(api.list).toHaveBeenCalledWith('profile-1', true);

    await (component as any).open(thread);
    expect(api.restore).not.toHaveBeenCalled();
    expect(router.navigate).toHaveBeenCalledWith(['/m', 'ask', 'answer'], {
      queryParams: { thread: 'thread-1' },
    });
  });

  it('archives active threads and removes them from the active list', async () => {
    (component as any).threads.set([thread]);
    await (component as any).archive(new Event('click'), thread);
    expect(api.archive).toHaveBeenCalledOnceWith('thread-1');
    expect((component as any).threads()).toEqual([]);
  });

  it('deletes a confirmed thread permanently', async () => {
    spyOn(window, 'confirm').and.returnValue(true);
    (component as any).threads.set([thread]);
    await (component as any).deleteThread(new Event('click'), thread);
    expect(api.delete).toHaveBeenCalledOnceWith('thread-1');
    expect((component as any).threads()).toEqual([]);
  });
});
