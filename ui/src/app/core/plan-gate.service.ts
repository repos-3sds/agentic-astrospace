import { Injectable, computed, inject } from '@angular/core';

import { EntitlementService } from './entitlement.service';

/** The plan a locked feature belongs to, as the paywall names it. */
export type GatedPlan = 'plus' | 'practitioner';

const CHECKS_KEY = 'astrospace.compat.checks';

/**
 * Which Explore features this reader's plan opens (Hawk, 2026-10-16).
 *
 * Free: the D1 chart, two yogas, every dosha by name with its cancellations,
 * one compatibility score a month, one remedy practice. Plus: the rest of
 * Explore. Practitioner: divisional charts and Practitioner mode.
 *
 * Gates follow the server's flags but only close once `quotas_enforced` is
 * on, the same switch that makes Ask limits block. Until store purchases are
 * live, nobody meets a lock with no way past it.
 */
@Injectable({ providedIn: 'root' })
export class PlanGateService {
  private readonly entitlements = inject(EntitlementService);

  /** Whether locks apply at all. */
  readonly live = computed(() => !!this.entitlements.current()?.quotas_enforced);

  constructor() {
    if (!this.entitlements.current()) void this.entitlements.refresh();
  }

  /** True when the plan includes the flag, or when locks are not live. */
  allows(key: string): boolean {
    const snapshot = this.entitlements.current();
    if (!snapshot?.quotas_enforced) return true;
    return snapshot.entitlements[key] === true;
  }

  /**
   * Whether this reader may open a compatibility report for `partnerId` this
   * month. Free counts distinct people per calendar month on the device;
   * re-opening a person already checked is always allowed.
   */
  allowsCompatibility(partnerId: string): boolean {
    const snapshot = this.entitlements.current();
    const limit = snapshot?.entitlements['compatibility.checks.period'];
    const checked = this.checkedThisMonth();
    if (checked.includes(partnerId)) return true;
    if (!snapshot?.quotas_enforced || typeof limit !== 'number') return true;
    return checked.length < limit;
  }

  /** Counts a compatibility check, whether or not locks are live. */
  recordCompatibility(partnerId: string): void {
    const checked = this.checkedThisMonth();
    if (checked.includes(partnerId)) return;
    try {
      localStorage.setItem(CHECKS_KEY, JSON.stringify({ month: monthKey(), ids: [...checked, partnerId] }));
    } catch {
      // Storage can be unavailable; the count is a courtesy, not a ledger.
    }
  }

  private checkedThisMonth(): string[] {
    try {
      const stored = JSON.parse(localStorage.getItem(CHECKS_KEY) ?? 'null') as { month?: string; ids?: string[] } | null;
      return stored?.month === monthKey() && Array.isArray(stored.ids) ? stored.ids : [];
    } catch {
      return [];
    }
  }
}

function monthKey(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}
