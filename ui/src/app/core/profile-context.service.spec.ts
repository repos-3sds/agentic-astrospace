import { TestBed } from '@angular/core/testing';

import { ApiService } from './api.service';
import { ProfileContextService } from './profile-context.service';

describe('ProfileContextService', () => {
  let service: ProfileContextService;
  let api: jasmine.SpyObj<ApiService>;

  beforeEach(() => {
    api = jasmine.createSpyObj<ApiService>('ApiService', ['get', 'post', 'patch', 'deleteWithBody']);
    TestBed.configureTestingModule({
      providers: [ProfileContextService, { provide: ApiService, useValue: api }],
    });
    service = TestBed.inject(ProfileContextService);
  });

  it('scopes reads to the selected profile', async () => {
    api.get.and.resolveTo({ profile_id: 'profile-a', revision: 0, facts: [] });
    await service.load('profile-a');
    expect(api.get).toHaveBeenCalledOnceWith('/profiles/profile-a/context');
  });

  it('sends revision, explicit consent and an idempotency key on create', async () => {
    api.post.and.resolveTo({ revision: 4, fact: {} as never });
    await service.create('profile-a', 3, {
      key: 'employment_status', value: { code: 'retired' }, valid_from: '2021-03-01',
    });
    const [path, body, headers] = api.post.calls.mostRecent().args;
    expect(path).toBe('/profiles/profile-a/context/facts');
    expect(body).toEqual(jasmine.objectContaining({
      expected_revision: 3,
      key: 'employment_status',
      consent: { state: 'granted', surface: 'profile_memory_v1' },
      source: { kind: 'profile_form', channel: 'profile_settings' },
    }));
    expect(headers?.['Idempotency-Key']).toMatch(/^create-/);
  });

  it('uses a correction source and preserves the governed key', async () => {
    api.patch.and.resolveTo({ revision: 5, fact: {} as never });
    await service.correct('profile-a', 'fact-1', 4, {
      key: 'occupation', value: { text: 'Teacher' },
    });
    expect(api.patch.calls.mostRecent().args[1]).toEqual(jasmine.objectContaining({
      expected_revision: 4,
      key: 'occupation',
      source: { kind: 'reader_correction', channel: 'profile_settings' },
    }));
  });

  it('confirms an Ask candidate with reader-statement provenance', async () => {
    api.post.and.resolveTo({ revision: 2, fact: {} as never });
    await service.createFromAsk('profile-a', 1, {
      key: 'relationship_status', value: { code: 'married' },
    }, 'I am married');
    const [, body, headers] = api.post.calls.mostRecent().args;
    expect(body).toEqual(jasmine.objectContaining({
      expected_revision: 1,
      source: { kind: 'reader_statement', channel: 'ask', excerpt: 'I am married' },
      consent: { state: 'granted', surface: 'ask_memory_confirmation_v1' },
    }));
    expect(headers?.['Idempotency-Key']).toMatch(/^ask-confirm-/);
  });

  it('corrects an existing Ask memory instead of creating a conflicting fact', async () => {
    api.patch.and.resolveTo({ revision: 3, fact: {} as never });
    await service.correctFromAsk('profile-a', 'existing-fact', 2, {
      key: 'employment_status', value: { code: 'retired' },
    }, 'I am retired');
    expect(api.patch.calls.mostRecent().args[0]).toBe(
      '/profiles/profile-a/context/facts/existing-fact',
    );
    expect(api.patch.calls.mostRecent().args[2]?.['Idempotency-Key']).toMatch(/^ask-correct-/);
  });

  it('deletes with the current revision and idempotency key', async () => {
    api.deleteWithBody.and.resolveTo({ revision: 6, fact_id: 'fact-1', status: 'deleted' });
    await service.remove('profile-a', 'fact-1', 5);
    expect(api.deleteWithBody.calls.mostRecent().args[0]).toBe(
      '/profiles/profile-a/context/facts/fact-1',
    );
    expect(api.deleteWithBody.calls.mostRecent().args[1]).toEqual({ expected_revision: 5 });
    expect(api.deleteWithBody.calls.mostRecent().args[2]?.['Idempotency-Key']).toMatch(/^delete-/);
  });
});
