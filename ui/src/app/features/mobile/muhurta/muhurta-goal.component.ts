import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { PreferencesService } from '../../../core/preferences.service';

/** One thing someone might be planning. */
export interface MuhurtaGoal {
  id: string;
  label: string;
  icon: string;
}

/** How far out to search. `custom` hands off to a date picker. */
export type MuhurtaRange = 'week' | 'month' | 'custom';

/**
 * Muhurta — Choose a goal (Figma node 30:56).
 *
 * Electional astrology, asked the way people actually ask it: not "compute a
 * muhurta" but "I am signing something, when is good". The goals are the
 * question in the reader's own words, which is also what keeps the answer
 * honest — a window is only meaningful for a stated purpose.
 *
 * "Something else" is not a fallback for a missing icon. Muhurta is asked about
 * things no fixed list will cover, and forcing an ill-fitting category would
 * produce a window computed for the wrong purpose.
 */
@Component({
  selector: 'as-muhurta-goal',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './muhurta-goal.component.html',
  styleUrl: './muhurta-goal.component.scss',
})
export class MuhurtaGoalComponent {
  readonly goals = signal<MuhurtaGoal[]>([
    { id: 'property', label: 'Buy property / gold', icon: 'goal-property' },
    { id: 'contract', label: 'Sign a contract', icon: 'goal-contract' },
    { id: 'journey', label: 'Start a journey', icon: 'goal-journey' },
    { id: 'venture', label: 'Start a new venture', icon: 'goal-venture' },
    { id: 'marriage', label: 'Marriage-related', icon: 'goal-marriage' },
    { id: 'other', label: 'Something else', icon: 'goal-other' },
  ]);

  readonly selectedGoal = signal<string>('contract');
  readonly range = signal<MuhurtaRange>('month');

  readonly ranges: { id: MuhurtaRange; label: string }[] = [
    { id: 'week', label: 'This week' },
    { id: 'month', label: 'This month' },
    { id: 'custom', label: 'Pick dates' },
  ];

  /**
   * Muhurta is local by definition — a window is sunrise-relative, so the same
   * instant is a different muhurta two cities apart. Stated on the screen
   * rather than assumed, because a reader travelling would otherwise get
   * windows for the wrong place without being told.
   */
  private readonly preferences = inject(PreferencesService);
  readonly place = computed(() => {
    const place = this.preferences.panchangaPlace();
    return place ? `${place.city}, ${place.nation}` : 'your panchanga place';
  });

  // Nothing can be computed for a purpose that has not been chosen.
  protected readonly canSearch = computed(() => this.selectedGoal().length > 0);

  private readonly router = inject(Router);

  protected findWindows(): void {
    if (!this.canSearch()) {
      return;
    }
    void this.router.navigate(['/m', 'muhurta', 'results'], {
      queryParams: { goal: this.selectedGoal(), range: this.range() },
    });
  }
}
