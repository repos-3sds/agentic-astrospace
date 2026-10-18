import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';

import { KundliStore } from '../../../core/kundli.store';
import { ProfileSwitcherComponent } from '../profile-switcher/profile-switcher.component';

/**
 * "Reading for Ravi Kumar · Change", shown only while the open chart is not
 * the account holder's. Greetings always address the holder (KundliStore.owner),
 * so without this a reader asking about "my" Moon period could get an answer
 * from a partner's chart and never notice (usability audit U8).
 */
@Component({
  selector: 'as-reading-for',
  standalone: true,
  imports: [ProfileSwitcherComponent],
  template: `
    @if (viewing(); as profile) {
      <button type="button" class="reading-for" (click)="open.set(true)"
              [attr.aria-label]="'Reading for ' + profile.name + '. Change profile'">
        <span class="mark" aria-hidden="true">{{ profile.name.slice(0, 1).toUpperCase() }}</span>
        <span>Reading for <b>{{ profile.name }}</b></span>
        <span class="change" aria-hidden="true">Change</span>
      </button>
    }
    @if (open()) {
      <as-profile-switcher (dismissed)="open.set(false)" />
    }
  `,
  styles: `
    @use '../mobile-tokens' as *;
    :host { display: contents; }
    .reading-for {
      @include m-body-small;
      @include m-pressable(0.98);
      display: inline-flex;
      align-items: center;
      gap: 8px;
      align-self: flex-start;
      min-height: 36px;
      padding: 4px 12px 4px 4px;
      border: 1px solid var(--m-border);
      border-radius: 999px;
      background: var(--m-raised);
      color: var(--m-text);
      cursor: pointer;
      b { font-weight: 600; }
    }
    .mark {
      display: grid;
      place-items: center;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: var(--m-accent-soft);
      color: var(--m-accent-strong);
      font-weight: 700;
    }
    .change { color: var(--m-accent-strong); font-weight: 600; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReadingForComponent {
  private readonly kundlis = inject(KundliStore);
  protected readonly open = signal(false);
  protected readonly viewing = computed(() => viewingSomeoneElse(this.kundlis));
}

/** The open profile when it is not the account holder's own, else null. */
export function viewingSomeoneElse(kundlis: KundliStore) {
  const active = kundlis.active();
  const owner = kundlis.owner();
  return active && owner && active.id !== owner.id ? active : null;
}
