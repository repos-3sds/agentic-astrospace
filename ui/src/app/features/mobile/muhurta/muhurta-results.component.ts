import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';

/** How strongly a window is endorsed. Two levels, not a score. */
export type WindowQuality = 'best' | 'good';

export interface MuhurtaWindow {
  rank: number;
  date: string;
  quality: WindowQuality;
  time: string;
  /** The rule that produced this window, named. */
  reason: string;
}

/**
 * Each phrase completes "Best times to …", so every one has to be a verb
 * phrase. The goal *labels* are noun-ish ("Marriage-related") and cannot be
 * dropped in directly — doing so produced "Best times to for a marriage
 * matter".
 */
const GOAL_PHRASES: Record<string, string> = {
  property: 'buy property or gold',
  contract: 'sign a contract',
  journey: 'start a journey',
  venture: 'start a new venture',
  marriage: 'plan something marriage-related',
  other: 'do what you’re planning',
};

const RANGE_LABELS: Record<string, string> = {
  week: 'This week',
  month: 'This month',
  custom: 'Your dates',
};

/**
 * Muhurta — Results (Figma node 31:57).
 *
 * Ranked windows for one stated purpose. Each carries the rule that produced
 * it — "Amrit Kalam overlaps a favourable Choghadiya", "Strong Abhijit
 * muhurta" — rather than a bare score, because those rules are exactly the
 * convention-dependent part: Choghadiya, Abhijit and the sunrise the whole
 * scheme hangs off all have more than one defensible reckoning. Naming the
 * rule is what lets a reader who follows a different tradition see that it is
 * a different tradition, and not a mistake. The place is in the subheading for
 * the same reason: a muhurta is sunrise-relative and does not travel.
 *
 * The closing line — timing supports the intent, the decision and diligence
 * are still the reader's — is the screen's point, not its disclaimer. An
 * auspicious window is not a warranty, and a contract signed in one is still a
 * contract someone has to read.
 */
@Component({
  selector: 'as-muhurta-results',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './muhurta-results.component.html',
  styleUrl: './muhurta-results.component.scss',
})
export class MuhurtaResultsComponent {
  private readonly params = toSignal(inject(ActivatedRoute).queryParamMap, {
    requireSync: true,
  });

  protected readonly heading = computed(() => {
    const goal = this.params().get('goal') ?? 'contract';
    return `Best times to ${GOAL_PHRASES[goal] ?? GOAL_PHRASES['other']}`;
  });

  protected readonly scope = computed(() => {
    const range = this.params().get('range') ?? 'month';
    return `${RANGE_LABELS[range] ?? RANGE_LABELS['month']} · ${this.place()}`;
  });

  readonly place = signal('Vijayawada');

  readonly windows = signal<MuhurtaWindow[]>([
    {
      rank: 1,
      date: 'Tuesday, 29 July',
      quality: 'best',
      time: '10:12 AM – 11:40 AM',
      reason:
        'Amrit Kalam overlaps a favourable Choghadiya, and the Moon supports new agreements.',
    },
    {
      rank: 2,
      date: 'Thursday, 31 July',
      quality: 'good',
      time: '4:05 PM – 5:30 PM',
      reason: 'Strong Abhijit muhurta; Mercury well-placed for paperwork.',
    },
    {
      rank: 3,
      date: 'Monday, 4 August',
      quality: 'good',
      time: '9:00 AM – 10:15 AM',
      reason: 'Favourable tarabala and a clear day-window with no major dosha.',
    },
  ]);
}
