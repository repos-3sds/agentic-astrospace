import { TestBed } from '@angular/core/testing';

import { ApiService } from './api.service';
import { AskService } from './ask.service';
import { AskResponse } from './models';

describe('AskService status handling', () => {
  let api: jasmine.SpyObj<ApiService>;
  let service: AskService;

  beforeEach(() => {
    api = jasmine.createSpyObj<ApiService>('ApiService', ['post']);
    TestBed.configureTestingModule({
      providers: [AskService, { provide: ApiService, useValue: api }],
    });
    service = TestBed.inject(AskService);
  });

  function lastAssistantMessage(kundliId: string) {
    const msgs = service.history(kundliId)();
    return msgs[msgs.length - 1];
  }

  it('tags an ordinary answered reply with status "answered"', async () => {
    api.post.and.resolveTo({
      answer: 'Your career looks strong this cycle.',
      tools_used: ['get_birth_chart'],
      status: 'answered',
    } as AskResponse);

    await service.ask('k1', 'What does my chart say about my career?');

    const msg = lastAssistantMessage('k1');
    expect(msg.status).toBe('answered');
    expect(msg.refer_out_kind).toBeUndefined();
  });

  it('never lets a domain_not_ready reply carry the answered status', async () => {
    api.post.and.resolveTo({
      answer: "Litigation isn't ready yet. I can currently help with: career, marriage.",
      tools_used: [],
      status: 'domain_not_ready',
    } as AskResponse);

    await service.ask('k1', 'Will I win my court case?');

    const msg = lastAssistantMessage('k1');
    expect(msg.status).toBe('domain_not_ready');
    expect(msg.status).not.toBe('answered');
  });

  it('never lets a clarification_needed reply carry the answered status', async () => {
    api.post.and.resolveTo({
      answer: 'I can help with: career, marriage right now — which one is this about?',
      tools_used: [],
      status: 'clarification_needed',
    } as AskResponse);

    await service.ask('k1', 'Tell me about it');

    const msg = lastAssistantMessage('k1');
    expect(msg.status).toBe('clarification_needed');
    expect(msg.status).not.toBe('answered');
  });

  it('carries refer_out_kind through on a refer_out reply', async () => {
    api.post.and.resolveTo({
      answer: 'That falls outside what I can responsibly speak to — please consult a professional.',
      tools_used: [],
      status: 'refer_out',
      refer_out_kind: 'health',
    } as AskResponse);

    await service.ask('k1', 'Do I have a fatal illness coming?');

    const msg = lastAssistantMessage('k1');
    expect(msg.status).toBe('refer_out');
    expect(msg.refer_out_kind).toBe('health');
  });
});
