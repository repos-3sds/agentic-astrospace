import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { PreferencesService } from '../../../core/preferences.service';

/** One thing someone might be planning. */
export interface MuhurtaGoal {
  id: string;
  label: string;
  icon: string;
  detail: string;
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
    { id: 'griha_pravesha', label: 'House warming', icon: 'goal-property', detail: 'Griha Pravesha' },
    { id: 'upanayana', label: 'Upanayana', icon: 'goal-venture', detail: 'Sacred-thread ceremony' },
    { id: 'marriage_related', label: 'Marriage-related', icon: 'goal-marriage', detail: 'Engagement or wedding work' },
    { id: 'namakarana', label: 'Naming ceremony', icon: 'goal-other', detail: 'Namakarana' },
    { id: 'annaprashana', label: 'First feeding', icon: 'goal-other', detail: 'Annaprashana' },
    { id: 'vidyarambha', label: 'Start learning', icon: 'goal-contract', detail: 'Vidyarambha' },
    { id: 'buy_property_gold', label: 'Buy property / gold', icon: 'goal-property', detail: 'Asset purchase' },
    { id: 'sign_contract', label: 'Sign a contract', icon: 'goal-contract', detail: 'Agreement or paperwork' },
    { id: 'start_journey', label: 'Start a journey', icon: 'goal-journey', detail: 'Travel departure' },
    { id: 'start_venture', label: 'Start a venture', icon: 'goal-venture', detail: 'Business beginning' },
    { id: 'general', label: 'Something else', icon: 'goal-other', detail: 'Tell us the intent' },
  ]);

  readonly selectedGoal = signal<string>('griha_pravesha');
  readonly range = signal<MuhurtaRange>('month');
  readonly customFrom = signal(this.isoDate(new Date()));
  readonly customTo = signal(this.isoDate(this.addDays(new Date(), 14)));
  readonly customIntent = signal('');

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
  protected readonly canSearch = computed(() => {
    if (!this.selectedGoal()) return false;
    if (this.selectedGoal() === 'general' && this.customIntent().trim().length < 6) return false;
    if (this.range() !== 'custom') return true;
    const from = this.customFrom();
    const to = this.customTo();
    return !!from && !!to && from <= to;
  });

  private readonly router = inject(Router);

  protected findWindows(): void {
    if (!this.canSearch()) {
      return;
    }
    const dates = this.selectedDates();
    const intent = this.customIntent().trim();
    void this.router.navigate(['/m', 'muhurta', 'results'], {
      queryParams: {
        goal: this.selectedGoal() === 'general' ? 'general' : this.selectedGoal(),
        intent: this.selectedGoal() === 'general' ? intent : null,
        range: this.range(),
        date_from: dates.from,
        date_to: dates.to,
      },
    });
  }

  protected setCustomFrom(value: string): void {
    this.customFrom.set(value);
    if (this.customTo() < value) this.customTo.set(value);
  }

  protected setCustomTo(value: string): void {
    this.customTo.set(value);
  }

  protected selectGoal(goal: string): void {
    this.selectedGoal.set(goal);
    if (goal !== 'general') this.customIntent.set('');
  }

  private selectedDates(): { from: string; to: string } {
    const today = new Date();
    if (this.range() === 'week') {
      return { from: this.isoDate(today), to: this.isoDate(this.addDays(today, 6)) };
    }
    if (this.range() === 'custom') {
      return { from: this.customFrom(), to: this.customTo() };
    }
    return { from: this.isoDate(today), to: this.isoDate(this.addDays(today, 30)) };
  }

  private addDays(date: Date, days: number): Date {
    const next = new Date(date);
    next.setDate(next.getDate() + days);
    return next;
  }

  private isoDate(date: Date): string {
    return date.toISOString().slice(0, 10);
  }
}
