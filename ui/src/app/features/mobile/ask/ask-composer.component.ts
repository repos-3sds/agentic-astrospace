import { ChangeDetectionStrategy, Component, ElementRef, inject, input, output } from '@angular/core';
import { ASK_NAVIGATION } from './ask-navigation';

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
    @if (navigation.web) {
      <textarea class="field" rows="3" [placeholder]="placeholder()" [attr.aria-label]="label()"
        [value]="value()" (input)="valueChange.emit($any($event.target).value)" (keydown)="onWebKey($event)"></textarea>
    }
    @if (voice()) {
      <button class="mic" type="button" aria-label="Ask by voice" (click)="voiceRequested.emit()">
        <span class="composer-icon mic-icon" aria-hidden="true"></span>
      </button>
    }
    @if (!navigation.web) { <input
      class="field"
      type="text"
      enterkeyhint="send"
      autocapitalize="sentences"
      [placeholder]="placeholder()"
      [attr.aria-label]="label()"
      [value]="value()"
      (input)="valueChange.emit($any($event.target).value)"
      (keydown.enter)="submit()"
    /> }
    <button
      class="send"
      type="button"
      aria-label="Send"
      [disabled]="!value().trim()"
      (click)="submit()"
    >
      <span class="composer-icon send-icon" aria-hidden="true"></span>
    </button>
  `,
  styleUrl: './ask-composer.component.scss',
  host: { '[class.is-inset]': 'inset()', '[class.web-composer]': '!!navigation.web' },
})
export class AskComposerComponent {
  protected readonly navigation = inject(ASK_NAVIGATION);
  protected onWebKey(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      this.submit();
    }
  }
  readonly value = input('');
  readonly placeholder = input('Ask a follow-up…');
  readonly label = input('Your question');
  /** Inset and floating (Ask Home) rather than edge to edge (the thread). */
  readonly inset = input(false);
  /** Show the microphone. Off where no host listens for `voiceRequested` or
   * where speech recognition is unavailable; a mic that does nothing is a lie. */
  readonly voice = input(false);

  readonly valueChange = output<string>();
  readonly submitted = output<string>();
  readonly voiceRequested = output<void>();

  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  /**
   * Put the caret at the end of the field, so a suggestion tapped into the
   * composer is ready to edit or send. Deferred a frame: the new value has to
   * reach the field before the caret can be placed after it.
   */
  focus(): void {
    requestAnimationFrame(() => {
      const field = this.host.nativeElement.querySelector<HTMLInputElement | HTMLTextAreaElement>('.field');
      if (!field) return;
      field.focus();
      const end = field.value.length;
      field.setSelectionRange(end, end);
    });
  }

  protected submit(): void {
    const q = this.value().trim();
    if (q) {
      this.submitted.emit(q);
    }
  }
}
