import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { BackLinkDirective } from '../../../core/back-link.directive';
import { StickyBarDirective } from './sticky-bar.directive';

/**
 * The one header for a screen below a tab: a bare chevron and the parent's
 * name, room for one trailing action, then the screen's serif title and an
 * optional one-line lede.
 *
 * The flow audit counted four header styles — this, a circled chevron with a
 * centred italic title, a circled chevron with an inline title, and a bare
 * chevron with a step counter. Sub-screens now all use this one; tab roots
 * keep their title-left, icon-right bar.
 *
 * The host is display: contents so the bar's sticky range is the whole
 * screen, not this element: it stays at the top while the title and the
 * page scroll under it.
 */
@Component({
  selector: 'as-back-bar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackLinkDirective, StickyBarDirective],
  template: `
    <div class="bar" asStickyBar>
      <a class="back" [asBack]="back()" [attr.aria-label]="'Back to ' + crumb()">
        <img src="mobile/back.svg" alt="" aria-hidden="true" />
        <span class="crumb">{{ crumb() }}</span>
      </a>
      <span class="action"><ng-content /></span>
    </div>
    @if (title()) {
      <div class="intro">
        <h1>{{ title() }}</h1>
        @if (lede()) { <p>{{ lede() }}</p> }
      </div>
    }
  `,
  styles: `
    @use '../mobile-tokens' as *;
    :host { display: contents; }
    .bar, .intro { flex-shrink: 0; }
    .bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 20px 4px;
    }
    .intro { display: flex; flex-direction: column; gap: 3px; padding: 4px 20px 12px; }
    h1 { @include m-h1; color: var(--m-text); margin: 0; }
    .intro p { @include m-body-small; color: var(--m-muted); margin: 0; }
    .back {
      display: flex;
      align-items: center;
      gap: 12px;
      min-height: 44px;
      min-width: 44px;
      text-decoration: none;
      img { width: 24px; height: 24px; display: block; filter: var(--m-back-icon-filter, none); }
    }
    .crumb { @include m-body-strong; color: var(--m-muted); }
    .action { display: flex; align-items: center; gap: 8px; }
  `,
})
export class BackBarComponent {
  /** Where back goes when there is no history to pop (see asBack). */
  readonly back = input.required<string | readonly unknown[] | null>();
  /** The parent screen's name, shown beside the chevron. */
  readonly crumb = input.required<string>();
  /** The screen's own name, set as its h1. */
  readonly title = input<string>('');
  readonly lede = input<string>('');
}
