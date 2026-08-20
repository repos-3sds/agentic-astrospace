import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import {
  EntitlementCatalog,
  EntitlementService,
  EntitlementSnapshot,
} from '../../../core/entitlement.service';
import { SubscriptionComponent } from './subscription.component';

const FREE: EntitlementSnapshot = {
  account_id: 'account-1', access_tier: 'free', account_topology: 'individual',
  offer_code: null, status: 'free', source: 'free_default',
  effective_at: '2026-08-18T00:00:00', expires_at: null, grace_ends_at: null,
  revision: 0, catalog_revision: 1,
  entitlements: { 'safety.guidance': true, 'reports.detailed': false },
  usage: {},
};

const CATALOG: EntitlementCatalog = {
  revision: 1,
  capabilities: {
    'safety.guidance': {
      kind: 'flag', description: 'Safety and refer-out guidance', protected_baseline: true,
    },
    'reports.detailed': {
      kind: 'flag', description: 'Detailed personal reports', protected_baseline: false,
    },
  },
};

describe('SubscriptionComponent', () => {
  let fixture: ComponentFixture<SubscriptionComponent>;
  let entitlements: jasmine.SpyObj<EntitlementService>;

  beforeEach(async () => {
    entitlements = jasmine.createSpyObj<EntitlementService>('EntitlementService', ['snapshot', 'catalog']);
    entitlements.snapshot.and.resolveTo(FREE);
    entitlements.catalog.and.resolveTo(CATALOG);
    await TestBed.configureTestingModule({
      imports: [SubscriptionComponent],
      providers: [provideRouter([]), { provide: EntitlementService, useValue: entitlements }],
    }).compileComponents();
    fixture = TestBed.createComponent(SubscriptionComponent);
  });

  it('renders the resolved plan and only capabilities included by the server', async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent || '';
    expect(text).toContain('CURRENT PLAN');
    expect(text).toContain('Free');
    expect(text).toContain('Safety and refer-out guidance');
    expect(text).not.toContain('Detailed personal reports');
    expect(text).toContain('Purchases are not available in this build');
    expect(text).not.toContain('Unlimited personal Ask');
  });

  it('renders an honest retry state without implying access changed', async () => {
    entitlements.snapshot.and.rejectWith(new Error('offline'));
    fixture = TestBed.createComponent(SubscriptionComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent || '';
    expect(text).toContain('Plans could not load');
    expect(text).toContain('Your current access has not changed');
  });
});
