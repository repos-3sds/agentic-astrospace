import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { PlanGateService } from '../../../core/plan-gate.service';
import { PreferencesService } from '../../../core/preferences.service';
import { ProfileSwitcherComponent } from '../profile-switcher/profile-switcher.component';

interface ExploreRow {
  id: string;
  label: string;
  detail: string;
  icon: string;
  route: string[];
  /** The plan flag that opens it fully; a row without one is free. */
  gate?: string;
  /** Free shows part of it, so the row says what is included rather than locking. */
  partial?: string;
}

/**
 * The Explore tab in Guided and Balanced (Hawk, 2026-10-16): eight entries
 * into the chart and its tools, the person they are about, and Settings
 * behind the gear. Practitioner keeps its Yantra workbench instead.
 *
 * Rows a plan does not include stay listed with a Plus mark, so the reader
 * can see what there is, and open to a screen that says what Plus adds.
 */
@Component({
  selector: 'as-explore-menu',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ProfileSwitcherComponent, RouterLink],
  templateUrl: './explore-menu.component.html',
  styleUrl: './explore-menu.component.scss',
})
export class ExploreMenuComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly gate = inject(PlanGateService);
  protected readonly preferences = inject(PreferencesService);

  protected readonly profileSwitcherOpen = signal(false);
  protected readonly profile = computed(() => {
    const name = this.kundlis.active()?.name ?? 'Choose a person';
    return { name, initial: name.slice(0, 1).toUpperCase() };
  });

  private readonly rows: ExploreRow[] = [
    { id: 'birth', label: 'Birth details', detail: 'Date, time and place', icon: 'set-profiles', route: ['/m', 'chart', 'birth-details'] },
    { id: 'chart', label: 'Your chart', detail: 'Rashi chart (D1)', icon: 'explore-varga', route: ['/m', 'chart'] },
    { id: 'yogas', label: 'Yogas & doshas', detail: 'Strengths and flags', icon: 'explore-yoga', route: ['/m', 'chart', 'yogas'], gate: 'yogas.full', partial: '2 yogas, every dosha' },
    { id: 'compat', label: 'Compatibility', detail: 'Match two people', icon: 'explore-compat', route: ['/m', 'compat'], gate: 'compatibility.full', partial: 'Score, 1 a month' },
    { id: 'readings', label: 'Readings', detail: 'Period readings, track record', icon: 'explore-readings', route: ['/m', 'readings'], gate: 'readings.full' },
    { id: 'remedies', label: 'Remedies', detail: 'Traditional practices', icon: 'remedy-rite', route: ['/m', 'remedies'], gate: 'remedies.full', partial: '1 practice' },
    { id: 'muhurta', label: 'Muhurtas', detail: 'Find a supportive time', icon: 'figma-yantra-calendar', route: ['/m', 'muhurta'], gate: 'muhurta.full' },
    { id: 'notes', label: 'Notes', detail: 'Your private reflections', icon: 'notes', route: ['/m', 'notes'] },
  ];

  protected readonly menu = computed(() => {
    // Read once so the list recomputes when the plan snapshot arrives.
    this.gate.live();
    return this.rows.map((row) => {
      const open = !row.gate || this.gate.allows(row.gate);
      return {
        ...row,
        detail: open || !row.partial ? row.detail : row.partial,
        locked: !open && !row.partial,
        partial: !open && !!row.partial,
      };
    });
  });
}
