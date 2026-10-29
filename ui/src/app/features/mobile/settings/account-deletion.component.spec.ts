import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { ApiService } from '../../../core/api.service';
import { AuthService } from '../../../core/auth.service';
import { EntitlementService, EntitlementSnapshot } from '../../../core/entitlement.service';
import { KundliStore } from '../../../core/kundli.store';
import { PurchaseService } from '../../../core/purchase.service';
import { AccountDeletionComponent } from './account-deletion.component';

describe('AccountDeletionComponent', () => {
  function render(snapshot: Partial<EntitlementSnapshot> | null): HTMLElement {
    const current = signal(snapshot as EntitlementSnapshot | null);
    TestBed.configureTestingModule({
      imports: [AccountDeletionComponent],
      providers: [
        provideRouter([]),
        { provide: ApiService, useValue: {} },
        { provide: AuthService, useValue: {} },
        { provide: KundliStore, useValue: { reset: () => undefined } },
        { provide: EntitlementService, useValue: { current, refresh: () => Promise.resolve() } },
        { provide: PurchaseService, useValue: { manageUrl: () => 'https://play.google.com/store/account/subscriptions' } },
      ],
    });
    const fixture = TestBed.createComponent(AccountDeletionComponent);
    fixture.detectChanges();
    return fixture.nativeElement;
  }

  it('asks a reader with a store plan to cancel it first (sweep G-3)', () => {
    const el = render({ source: 'revenuecat', access_tier: 'plus' });
    const note = el.querySelector('.store-plan')?.textContent ?? '';
    expect(note).toContain('Cancel your Plus plan first');
    expect(note).toContain('does not stop that billing');
    expect(el.querySelector('.store-plan button')?.textContent).toContain('Cancel in Google Play');
  });

  it('says nothing for a free account or one not billed by a store', () => {
    expect(render({ source: 'free', access_tier: 'free' }).querySelector('.store-plan')).toBeNull();
    TestBed.resetTestingModule();
    expect(render({ source: 'override', access_tier: 'pro' }).querySelector('.store-plan')).toBeNull();
  });
});
