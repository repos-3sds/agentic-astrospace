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
});
