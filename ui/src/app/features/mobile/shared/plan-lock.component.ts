import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { GatedPlan } from '../../../core/plan-gate.service';

/**
 * A feature this plan does not include: what it is, which plan has it, and
 * one way to see that plan. Calm by design. A lock is never a warning about
 * the reader's chart, and nothing here sells relief from a dosha.
 */
@Component({
  selector: 'as-plan-lock',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <section class="lock" [class.is-compact]="compact()">
      <span class="mark" aria-hidden="true"></span>
      <div class="copy">
        <p class="eyebrow">{{ plan() === 'practitioner' ? 'PRACTITIONER PLAN' : 'PART OF PLUS' }}</p>
        <h2>{{ title() }}</h2>
        @if (body()) { <p class="body">{{ body() }}</p> }
      </div>
      <a class="cta" routerLink="/m/subscription" [queryParams]="params()">
        {{ plan() === 'practitioner' ? 'See Practitioner' : 'See Plus' }}
      </a>
    </section>
  `,
  styles: `
    @use '../mobile-tokens' as *;
    :host { display: block; }
    .lock {
      display: flex; flex-direction: column; align-items: flex-start; gap: 10px;
      padding: 18px; border: 1px solid var(--m-border); border-radius: 20px;
      background: var(--m-surface); box-shadow: var(--m-shadow-card);
    }
    .lock.is-compact { flex-direction: row; align-items: center; padding: 14px 16px; gap: 12px; }
    .is-compact .copy { flex: 1 1 auto; min-width: 0; }
    .is-compact h2 { @include m-body-strong; }
    .mark {
      flex: 0 0 auto; width: 36px; height: 36px; border-radius: 12px; background: var(--m-accent-soft);
      display: block; position: relative;
      &::after {
        content: ''; position: absolute; inset: 9px; background: var(--m-accent-strong);
        -webkit-mask: url('/mobile/lock.svg') center / contain no-repeat;
        mask: url('/mobile/lock.svg') center / contain no-repeat;
      }
    }
    .copy { display: flex; flex-direction: column; gap: 4px; }
    .eyebrow { @include m-eyebrow; color: var(--m-accent-strong); margin: 0; }
    h2 { @include m-h2; color: var(--m-text); margin: 0; }
    .body { @include m-body-small; color: var(--m-muted); margin: 0; }
    .cta { @include m-cta-primary; min-height: 44px; padding-inline: 20px; text-decoration: none; flex: 0 0 auto; }
  `,
})
export class PlanLockComponent {
  readonly plan = input<GatedPlan>('plus');
  readonly title = input.required<string>();
  readonly body = input<string>('');
  /** The feature key, so Plans can say what brought the reader there. */
  readonly from = input<string>('');
  readonly compact = input(false);

  protected readonly params = computed(() => ({ from: this.from() || null, plan: this.plan() }));
}
