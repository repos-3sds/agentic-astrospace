import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { EntitlementService } from '../../../core/entitlement.service';
import { HapticsService } from '../../../core/haptics.service';
import { KundliStore } from '../../../core/kundli.store';
import { Kundli } from '../../../core/models';
import { PROFILE_RELATIONSHIPS, normalizeProfileRelationship } from '../settings/profile-fields';
import { GenericErrorComponent } from '../states/generic-error.component';

/** Relations read as "family"; everyone else saved on the account is listed apart. */
const FAMILY_RELATIONS = new Set(['self', 'spouse', 'partner', 'child', 'parent', 'grandparent', 'grandchild', 'sibling', 'relative']);

interface FamilyGroup {
  label: string;
  people: Kundli[];
}

/**
 * Family — the third tab of the Ask-first app (checklist D1).
 *
 * Most people open an astrology app for someone other than themselves as
 * often as for themselves: a child's naming, a parent's period, a match. The
 * profiles were already there, buried under Settings › Profiles; this puts
 * them a tab away and makes the two things people do with them obvious —
 * switch whose reading Today and Ask show, and match two people.
 *
 * Switching here never navigates. The person stays on the list, sees the
 * "Viewing" mark move, and goes to Today when they choose; jumping away on a
 * tap would make a mis-tap expensive.
 */
@Component({
  selector: 'as-family',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [GenericErrorComponent, RouterLink],
  templateUrl: './family.component.html',
  styleUrl: './family.component.scss',
})
export class FamilyComponent {
  protected readonly kundlis = inject(KundliStore);
  private readonly entitlements = inject(EntitlementService);
  private readonly haptics = inject(HapticsService);

  protected readonly loading = signal(!this.kundlis.loaded());
  protected readonly error = signal<string | null>(null);

  protected readonly activeName = computed(() => this.kundlis.active()?.name ?? 'you');

  protected readonly groups = computed<FamilyGroup[]>(() => {
    const people = [...this.kundlis.kundlis()];
    // "Myself" first, then by relation order in the form, then by name.
    const order = (profile: Kundli) =>
      PROFILE_RELATIONSHIPS.findIndex((option) => option.value === normalizeProfileRelationship(profile.relation));
    people.sort((a, b) => order(a) - order(b) || a.name.localeCompare(b.name));
    const family = people.filter((profile) => FAMILY_RELATIONS.has(normalizeProfileRelationship(profile.relation)));
    const others = people.filter((profile) => !FAMILY_RELATIONS.has(normalizeProfileRelationship(profile.relation)));
    return [
      { label: 'FAMILY', people: family },
      { label: 'FRIENDS & OTHERS', people: others },
    ].filter((group) => group.people.length);
  });

  /** "2 of 2 profiles" only when a limit is actually applied; otherwise silent. */
  protected readonly capacity = computed(() => {
    const snapshot = this.entitlements.current();
    const limit = snapshot?.entitlements?.['profiles.max'];
    if (!snapshot?.quotas_enforced || typeof limit !== 'number') return null;
    const used = this.kundlis.kundlis().length;
    return { used, limit, full: used >= limit };
  });

  constructor() {
    void this.load();
    if (!this.entitlements.current()) void this.entitlements.refresh().catch(() => undefined);
  }

  protected reload(): void {
    void this.load();
  }

  protected relationLabel(profile: Kundli): string {
    const relation = normalizeProfileRelationship(profile.relation);
    return PROFILE_RELATIONSHIPS.find((option) => option.value === relation)?.label ?? 'Profile';
  }

  protected signs(profile: Kundli): string {
    return profile.moon_sign ? `${profile.moon_sign} Moon` : profile.birth_city;
  }

  protected isActive(profile: Kundli): boolean {
    return profile.id === this.kundlis.activeId();
  }

  protected view(profile: Kundli): void {
    if (this.isActive(profile)) return;
    this.haptics.select();
    this.kundlis.setActive(profile.id);
  }

  private async load(): Promise<void> {
    this.error.set(null);
    try {
      await this.kundlis.load();
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }
}
