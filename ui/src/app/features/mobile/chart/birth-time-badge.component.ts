import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { Kundli, birthTimeIsApproximate } from '../../../core/models';

/**
 * "APPROXIMATE BIRTH TIME" flag for screens whose numbers depend on the hour:
 * houses, the ascendant, and every dasha date. Renders nothing for an exact
 * time, so consumers drop it in unconditionally. A chart cast from a guess
 * has to say so wherever the guess shows — stating the rule used, rather
 * than implying precision, is the same principle as `observance_note`.
 */
@Component({
  selector: 'as-birth-time-badge',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (approximate()) {
      <span class="badge" role="note">
        <span class="label">Approximate birth time</span>
        @if (detail()) { <span class="detail">{{ detail() }}</span> }
      </span>
    }
  `,
  styles: `
    @use '../mobile-tokens' as *;
    :host { display: contents; }
    .badge {
      display: inline-flex; flex-wrap: wrap; align-items: baseline; gap: 4px 8px;
      max-width: 100%;
    }
    .label {
      @include m-badge;
      color: var(--m-text);
      background: var(--m-warn-soft);
      border: 1px solid color-mix(in srgb, var(--m-warn) 55%, transparent);
      text-transform: uppercase; letter-spacing: 0.04em;
    }
    .detail { @include m-caption; color: var(--m-muted); }
  `,
})
export class BirthTimeBadgeComponent {
  readonly profile = input<Pick<Kundli, 'birth_time_accuracy' | 'notes'> | null | undefined>(null);
  /** What the estimate affects on this particular screen. Omit for the bare chip. */
  readonly detail = input<string>('');
  protected readonly approximate = computed(() => birthTimeIsApproximate(this.profile()));
}
