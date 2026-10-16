import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { EntitlementService, EntitlementSnapshot, StoreProduct } from '../../../core/entitlement.service';
import { KundliStore } from '../../../core/kundli.store';
import { PurchaseService } from '../../../core/purchase.service';
import { SubscriptionComponent } from './subscription.component';

const FREE: EntitlementSnapshot = {
  account_id: 'account-1', access_tier: 'free', account_topology: 'individual',
  offer_code: null, status: 'free', source: 'free_default',
  effective_at: '2026-08-18T00:00:00', expires_at: null, grace_ends_at: null,
  revision: 0, catalog_revision: 2,
  entitlements: { 'ask.answers.period': 3, 'profiles.max': 2 },
  usage: { 'ask.answers.period': { used: 1, reserved: 0, remaining: 2, resets_at: '2026-11-01T00:00:00', period_id: '2026-10' } },
  question_credits: 0,
  quotas_enforced: true,
};

const PRODUCTS: StoreProduct[] = [
  { id: 'siddha_plus_monthly', kind: 'plan', title: 'Plus, monthly', price_inr: 299, tier: 'plus', months: 1, questions: null },
  { id: 'siddha_plus_yearly', kind: 'plan', title: 'Plus, yearly', price_inr: 1999, tier: 'plus', months: 12, questions: null },
  { id: 'siddha_questions_3', kind: 'question_pack', title: '3 questions', price_inr: 99, tier: null, months: null, questions: 3 },
];

describe('SubscriptionComponent', () => {
  let fixture: ComponentFixture<SubscriptionComponent>;
  let snapshot: jasmine.Spy;
  const current = signal<EntitlementSnapshot | null>(null);

  beforeEach(async () => {
    snapshot = jasmine.createSpy('snapshot').and.callFake(async () => { current.set(FREE); return FREE; });
    await TestBed.configureTestingModule({
      imports: [SubscriptionComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        {
          provide: EntitlementService,
          useValue: {
            snapshot,
            current,
            askAllowance: signal({ limit: 3, used: 1, remaining: 2, credits: 0, resetsAt: null, enforced: true }),
            products: async () => ({ products: PRODUCTS, quotas_enforced: true }),
          },
        },
        { provide: KundliStore, useValue: { load: async () => undefined, kundlis: signal([{ id: 'k1' }]) } },
        {
          provide: PurchaseService,
          useValue: {
            init: async () => undefined,
            available: signal(false),
            unavailableReason: signal('not_configured'),
            prices: signal({}),
            manageUrl: () => '',
          },
        },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(SubscriptionComponent);
  });

  async function render(): Promise<string> {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    return (fixture.nativeElement as HTMLElement).textContent || '';
  }

  it('shows usage, D2 prices, the always-free list and an honest store state', async () => {
    const text = await render();
    expect(text).toContain('1 of 3');
    expect(text).toContain('1 of 2');
    expect(text).toContain('₹1,999 a year');
    expect(text).toContain('₹299 a month');
    expect(text).toContain('₹99, once');
    expect(text).toContain('Every dosha by name, with its cancellations');
    expect(text).toContain('Purchases open once AstroSpace is live');
    const cta = (fixture.nativeElement as HTMLElement).querySelector<HTMLButtonElement>('.cta')!;
    expect(cta.disabled).toBeTrue();
  });

  it('renders an honest retry state without implying access changed', async () => {
    snapshot.and.rejectWith(new Error('offline'));
    const text = await render();
    expect(text).toContain('Plans could not load');
    expect(text).toContain('Your current access has not changed');
  });
});
