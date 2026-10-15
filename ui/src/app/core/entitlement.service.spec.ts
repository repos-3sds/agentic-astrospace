import { TestBed } from '@angular/core/testing';
import { ApiService } from './api.service';
import { EntitlementService } from './entitlement.service';

describe('EntitlementService', () => {
  let service: EntitlementService;
  let api: jasmine.SpyObj<ApiService>;

  beforeEach(() => {
    api = jasmine.createSpyObj<ApiService>('ApiService', ['get']);
    TestBed.configureTestingModule({
      providers: [EntitlementService, { provide: ApiService, useValue: api }],
    });
    service = TestBed.inject(EntitlementService);
  });

  it('reads the server-authoritative snapshot and catalog', async () => {
    api.get.and.resolveTo({});
    await service.snapshot();
    await service.catalog();
    expect(api.get.calls.allArgs()).toEqual([
      ['/entitlements'],
      ['/entitlements/catalog'],
    ]);
  });

  it('derives the Ask allowance from the snapshot', async () => {
    api.get.and.resolveTo({
      access_tier: 'free', entitlements: { 'ask.answers.period': 3 }, question_credits: 2, quotas_enforced: true,
      usage: { 'ask.answers.period': { used: 2, reserved: 1, remaining: 0, resets_at: '2026-11-01T00:00:00', period_id: '2026-10' } },
    });
    await service.snapshot();
    expect(service.askAllowance()).toEqual({
      limit: 3, used: 3, remaining: 0, credits: 2, resetsAt: '2026-11-01T00:00:00', enforced: true,
    });
  });
});
