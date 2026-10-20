import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { EntitlementDenial } from '../../../core/entitlement-denial';

/**
 * The one card for "a plan or limit stopped this": Ask's monthly answers,
 * the profile count, a Plus-only feature. Says what happened, when it comes
 * back on its own, and the two ways forward, without urgency or fear: a
 * reached limit is a pause, never a warning about the reader's chart.
 */
@Component({
  selector: 'as-locked-state',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <section class="locked" role="status">
      <span class="mark" aria-hidden="true"></span>
      <h2>{{ title() }}</h2>
      <p>{{ body() }}</p>
      <div class="actions">
        <a class="primary" routerLink="/m/subscription" [queryParams]="{ from: denial().entitlement }">See plans</a>
        @if (isAsk()) {
          <a class="secondary" routerLink="/m/subscription" [queryParams]="{ from: denial().entitlement, focus: 'packs' }">Buy questions</a>
        }
      </div>
      @if (isAsk()) {
        <small>Refer-outs, clarifications and answers that fail never use a question.</small>
      }
    </section>
  `,
  styles: `
    @use '../mobile-tokens' as *;
    :host { display: block; }
    .locked {
      display: flex; flex-direction: column; align-items: flex-start; gap: 8px;
      padding: 18px; border: 1px solid var(--m-border); border-radius: 20px;
      background: var(--m-surface); box-shadow: var(--m-shadow-card);
    }
    .mark {
      width: 36px; height: 36px; border-radius: 12px; background: var(--m-accent-soft);
      display: block; position: relative;
      &::after {
        content: ''; position: absolute; inset: 9px; background: var(--m-accent-strong);
        -webkit-mask: url('/mobile/sparkle.svg') center / contain no-repeat;
        mask: url('/mobile/sparkle.svg') center / contain no-repeat;
      }
    }
    h2 { @include m-h2; color: var(--m-text); margin: 4px 0 0; }
    p { @include m-body-small; color: var(--m-muted); margin: 0; }
    small { @include m-caption; color: var(--m-muted); }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px; }
    .primary { @include m-cta-primary; min-height: 44px; padding-inline: 20px; text-decoration: none; }
    .secondary { @include m-cta-secondary; min-height: 44px; padding-inline: 18px; text-decoration: none; color: var(--m-text); }
  `,
})
export class LockedStateComponent {
  readonly denial = input.required<EntitlementDenial>();

  protected readonly isAsk = computed(() => this.denial().entitlement === 'ask.answers.period');

  protected readonly title = computed(() => {
    const d = this.denial();
    if (d.entitlement === 'ask.answers.period') {
      return welcomeOnly(d) ? 'Your free question is used' : 'You’ve used this month’s answers';
    }
    if (d.entitlement === 'profiles.max') return 'Your profiles are full';
    if (d.entitlement === 'readings.period') return 'You’ve used this month’s readings';
    return 'Part of Plus';
  });

  protected readonly body = computed(() => {
    const d = this.denial();
    const back = resetSentence(d.resets_at);
    if (d.entitlement === 'ask.answers.period') {
      return welcomeOnly(d)
        ? 'Your free question is used. Plus gives you 5 answers a month, or buy a question for ₹49.'
        : `Your answers for this month are used.${back} A question pack adds more right away.`;
    }
    if (d.entitlement === 'profiles.max') {
      return d.access_tier === 'free'
        ? 'Free keeps 1 profile. Plus keeps 3, or remove one you no longer need.'
        : 'Your plan’s profile slots are in use. Remove one you no longer need to add another.';
    }
    if (d.entitlement === 'readings.period') {
      return `Your free readings for this month are used.${back} Plus writes a reading for every period.`;
    }
    return 'This is included with Plus. Everything about safety, your sources and your own data stays free.';
  });
}

/** Free with no monthly allowance: only the one welcome question. */
function welcomeOnly(d: EntitlementDenial): boolean {
  return d.access_tier === 'free' && !d.limit;
}

function resetSentence(resetsAt: string | null): string {
  if (!resetsAt) return '';
  const date = new Date(resetsAt.endsWith('Z') || /[+-]\d\d:\d\d$/.test(resetsAt) ? resetsAt : `${resetsAt}Z`);
  if (Number.isNaN(date.getTime())) return '';
  const label = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'long', timeZone: 'UTC' }).format(date);
  return ` They come back on ${label}.`;
}
