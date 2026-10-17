import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { BackLinkDirective } from '../../../core/back-link.directive';
import { SubhashitaService, SUBHASHITA_TITLE } from '../../../core/subhashita.service';
import { SubhashitaVerseComponent } from './subhashita-verse.component';

/**
 * Today's Subhashita, from Explore, the morning push and the widget. Only
 * today's verse: there is no archive to page back through (Hawk, 2026-10-17).
 */
@Component({
  selector: 'as-subhashita',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackLinkDirective, SubhashitaVerseComponent],
  template: `
    <a class="appbar" [asBack]="['/m', 'explore']">
      <img src="mobile/back.svg" alt="" aria-hidden="true" />
      <span class="crumb">Explore</span>
    </a>

    <div class="body">
      <header class="intro">
        <h1 class="title">{{ title }}</h1>
        <p class="lede">A verse a day from the Bhagavad Gita, Chanakya Niti and the Puranas. A new one arrives each day.</p>
      </header>

      @if (subhashita.today(); as verse) {
        <as-subhashita-verse [verse]="verse" />
      } @else if (subhashita.error()) {
        <p class="state" role="alert">Today’s verse could not be loaded. Check your connection and try again.</p>
        <button class="retry" type="button" (click)="subhashita.load()">Try again</button>
      } @else {
        <p class="state" aria-live="polite">Finding today’s verse…</p>
      }
    </div>
  `,
  styleUrl: './subhashita.component.scss',
})
export class SubhashitaComponent {
  protected readonly subhashita = inject(SubhashitaService);
  protected readonly title = SUBHASHITA_TITLE;

  constructor() {
    void this.subhashita.load();
  }
}
