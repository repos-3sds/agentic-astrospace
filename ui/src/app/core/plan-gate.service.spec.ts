import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { EntitlementService, EntitlementSnapshot } from './entitlement.service';
import { PlanGateService } from './plan-gate.service';

function snapshot(enforced: boolean, entitlements: Record<string, boolean | number | null>): EntitlementSnapshot {
  return {
    account_id: 'a', access_tier: 'free', account_topology: 'individual', offer_code: null, status: 'active',
    source: 'default', effective_at: '', expires_at: null, grace_ends_at: null, revision: 1, catalog_revision: 3,
    entitlements, usage: {}, quotas_enforced: enforced,
  };
}

describe('PlanGateService', () => {
  const current = signal<EntitlementSnapshot | null>(null);
  let gate: PlanGateService;

  beforeEach(() => {
    localStorage.removeItem('astrospace.compat.checks');
    current.set(null);
    TestBed.configureTestingModule({
      providers: [{ provide: EntitlementService, useValue: { current, refresh: () => Promise.resolve() } }],
    });
    gate = TestBed.inject(PlanGateService);
  });

  it('opens everything until plans are enforced', () => {
    current.set(snapshot(false, { 'readings.full': false }));
    expect(gate.allows('readings.full')).toBeTrue();
  });

  it('follows the plan flag once enforced', () => {
    current.set(snapshot(true, { 'readings.full': false, 'yogas.full': true }));
    expect(gate.allows('readings.full')).toBeFalse();
    expect(gate.allows('yogas.full')).toBeTrue();
  });

  it('allows one compatibility person a month on Free, and reopening that person', () => {
    current.set(snapshot(true, { 'compatibility.checks.period': 1 }));
    expect(gate.allowsCompatibility('p1')).toBeTrue();
    gate.recordCompatibility('p1');
    expect(gate.allowsCompatibility('p1')).toBeTrue();
    expect(gate.allowsCompatibility('p2')).toBeFalse();
  });

  it('counts checks but does not block before plans are enforced', () => {
    current.set(snapshot(false, { 'compatibility.checks.period': 1 }));
    gate.recordCompatibility('p1');
    expect(gate.allowsCompatibility('p2')).toBeTrue();
  });
});
