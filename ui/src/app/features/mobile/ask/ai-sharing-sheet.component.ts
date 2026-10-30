import { ChangeDetectionStrategy, Component, output } from '@angular/core';

import { openLegal } from '../../../core/legal';
import { SheetComponent } from '../sheet/sheet.component';

/**
 * Asked once, before a reader's first question leaves the phone, when they
 * have not already agreed on the setup screen ("Written with AI").
 *
 * Apple's App Review guideline 5.1.2(i): an app must say plainly when
 * personal data goes to a third-party AI, and get the reader's permission
 * first. The Privacy Policy names the same providers; this is the in-app
 * moment it happens.
 */
@Component({
  selector: 'as-ai-sharing-sheet',
  standalone: true,
  imports: [SheetComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <as-sheet (dismissed)="dismissed.emit()">
      <header class="head">
        <h2 class="title">Answers are written by our Siddha Agents</h2>
        <p class="sub">
          To answer, our Siddha Agents use your question and your chart details.
          They never see your email address.
        </p>
      </header>
      <button class="link" type="button" (click)="privacy()">Read the Privacy Policy</button>
      <button class="send" type="button" (click)="agreed.emit()">Agree and ask</button>
      <button class="later" type="button" (click)="dismissed.emit()">Not now</button>
    </as-sheet>
  `,
  styles: `
    @use '../mobile-tokens' as *;
    :host { display: contents; }
    .head { display: flex; flex-direction: column; gap: 6px; }
    .title { @include m-h2; color: var(--m-text); margin: 0; }
    .sub { @include m-body-small; color: var(--m-muted); margin: 0; }
    .link {
      @include m-body-small;
      align-self: flex-start;
      padding: 0;
      border: 0;
      background: none;
      color: var(--m-accent);
      text-decoration: underline;
      cursor: pointer;
    }
    .send { @include m-cta-primary; width: 100%; }
    .later {
      @include m-body-strong;
      width: 100%;
      min-height: 44px;
      border: 0;
      background: none;
      color: var(--m-muted);
      cursor: pointer;
    }
  `,
})
export class AiSharingSheetComponent {
  readonly agreed = output<void>();
  readonly dismissed = output<void>();

  protected privacy(): void {
    void openLegal('privacy');
  }
}
