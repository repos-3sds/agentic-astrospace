import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

/**
 * The Ask composer — mic, field, send (Figma nodes 25:75, 26:93, 27:113).
 *
 * Shared by every Ask screen. The three designs differ only in how the pill is
 * seated: Ask Home floats it inset over the suggestions, the thread screens run
 * it edge to edge. That is the `inset` input; everything else is identical, and
 * keeping one copy is what stops the send button from drifting between screens.
 */
@Component({
  selector: 'as-ask-composer',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <button class="mic" type="button" aria-label="Ask by voice" (click)="voiceRequested.emit()">
      <img src="mobile/mic.svg" alt="" aria-hidden="true" />
    </button>
    <input
      class="field"
      type="text"
      [placeholder]="placeholder()"
      [attr.aria-label]="label()"
      [value]="value()"
      (input)="valueChange.emit($any($event.target).value)"
      (keydown.enter)="submit()"
    />
    <button
      class="send"
      type="button"
      aria-label="Send"
      [disabled]="!value().trim()"
      (click)="submit()"
    >
      <img src="mobile/send.svg" alt="" aria-hidden="true" />
    </button>
  `,
  styleUrl: './ask-composer.component.scss',
  host: { '[class.is-inset]': 'inset()' },
})
export class AskComposerComponent {
  readonly value = input('');
  readonly placeholder = input('Ask a follow-up…');
  readonly label = input('Your question');
  /** Inset and floating (Ask Home) rather than edge to edge (the thread). */
  readonly inset = input(false);

  readonly valueChange = output<string>();
  readonly submitted = output<string>();
  readonly voiceRequested = output<void>();

  protected submit(): void {
    const q = this.value().trim();
    if (q) {
      this.submitted.emit(q);
    }
  }
}
