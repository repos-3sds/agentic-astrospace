import { ChangeDetectionStrategy, Component, ElementRef, computed, inject, input, output, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { KundliStore } from '../../../core/kundli.store';
import { ProfileSwitcherComponent } from '../profile-switcher/profile-switcher.component';
import { AskDepthService } from './ask-depth.service';
import { ASK_NAVIGATION } from './ask-navigation';

/**
 * The Ask composer — mic, field, send (Figma nodes 25:75, 26:93, 27:113).
 *
 * Shared by every Ask screen. The three designs differ only in how the pill is
 * seated: Ask Home floats it inset over the suggestions, the thread screens run
 * it edge to edge. That is the `inset` input; everything else is identical, and
 * keeping one copy is what stops the send button from drifting between screens.
 *
 * Two rows, like the big chat apps (Hawk, 2026-10-29): the field gets the
 * whole width, and the tools sit under it. "+" opens a menu with "Ask about
 * someone" (the profile switcher), "Add a family member" and "Deep answer"
 * with a tick. The chips beside "+" show whose chart is read and whether Deep
 * (AskDepthService) is on, and each is a one-tap switch.
 */
@Component({
  selector: 'as-ask-composer',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (menuOpen()) {
      <button class="menu-scrim" type="button" aria-label="Close menu" tabindex="-1" (click)="menuOpen.set(false)"></button>
      <div class="menu" role="menu" aria-label="Ask options">
        <button class="menu-row" type="button" role="menuitem" (click)="choosePerson()">
          <span class="menu-mark"><span class="composer-icon person-icon" aria-hidden="true"></span></span>
          <span class="menu-copy"><strong>Ask about someone</strong><small>Now: {{ personName() }}</small></span>
        </button>
        <a class="menu-row" role="menuitem" routerLink="/m/settings/profiles/new" (click)="menuOpen.set(false)">
          <span class="menu-mark"><span class="composer-icon person-add-icon" aria-hidden="true"></span></span>
          <span class="menu-copy"><strong>Add a family member</strong><small>Their birth details, saved as a profile</small></span>
        </a>
        <button class="menu-row" type="button" role="menuitemcheckbox" [attr.aria-checked]="deep()" (click)="toggleDepth()">
          <span class="menu-mark" [class.on]="deep()"><span class="composer-icon deep-icon" aria-hidden="true"></span></span>
          <span class="menu-copy" [class.on]="deep()"><strong>Deep answer</strong><small>Reads your chart from every side · about a minute</small></span>
          @if (deep()) { <span class="composer-icon tick-icon" aria-hidden="true"></span> }
        </button>
      </div>
    }
    @if (navigation.web) {
      <textarea class="field" rows="3" [placeholder]="placeholder()" [attr.aria-label]="label()"
        [value]="value()" (input)="valueChange.emit($any($event.target).value)" (keydown)="onWebKey($event)"></textarea>
    } @else {
      <input
        class="field"
        type="text"
        enterkeyhint="send"
        autocapitalize="sentences"
        [placeholder]="deep() ? 'Ask in depth…' : placeholder()"
        [attr.aria-label]="label()"
        [value]="value()"
        (input)="valueChange.emit($any($event.target).value)"
        (keydown.enter)="submit()"
      />
    }
    <div class="tools">
      <button class="more" type="button" aria-label="Ask options" aria-haspopup="menu"
        [attr.aria-expanded]="menuOpen()" (click)="menuOpen.set(!menuOpen())">
        <span class="composer-icon plus-icon" aria-hidden="true"></span>
      </button>
      <button class="chip person" type="button" [attr.aria-label]="'Asking about ' + personName() + '. Change'" (click)="choosePerson()">
        <span class="composer-icon person-icon" aria-hidden="true"></span><span class="chip-text">{{ personName() }}</span>
      </button>
      <button
        class="chip depth"
        type="button"
        [class.on]="deep()"
        [attr.aria-pressed]="deep()"
        [attr.aria-label]="deep() ? 'Deep answer on: reads your chart from every side, about a minute' : 'Deep answer off: quick answer'"
        (click)="toggleDepth()"
      >
        <span class="composer-icon deep-icon" aria-hidden="true"></span><span class="chip-text">Deep</span>
      </button>
      <span class="spacer"></span>
      @if (voice()) {
        <button class="mic" type="button" aria-label="Ask by voice" (click)="voiceRequested.emit()">
          <span class="composer-icon mic-icon" aria-hidden="true"></span>
        </button>
      }
      <button
        class="send"
        type="button"
        aria-label="Send"
        [disabled]="!value().trim()"
        (click)="submit()"
      >
        <span class="composer-icon send-icon" aria-hidden="true"></span>
      </button>
    </div>
    @if (switching()) {
      <as-profile-switcher (dismissed)="switching.set(false)" />
    }
  `,
  styleUrl: './ask-composer.component.scss',
  imports: [RouterLink, ProfileSwitcherComponent],
  host: {
    '[class.is-inset]': 'inset()',
    '[class.web-composer]': '!!navigation.web',
    '(document:keydown.escape)': 'menuOpen.set(false)',
  },
})
export class AskComposerComponent {
  protected readonly navigation = inject(ASK_NAVIGATION);
  protected readonly depthService = inject(AskDepthService);
  protected readonly deep = computed(() => this.depthService.depth() === 'deep');
  private readonly kundlis = inject(KundliStore);
  /** Whose chart the question is read from: the open profile, first name. */
  protected readonly personName = computed(() => this.kundlis.active()?.name.split(' ')[0] ?? 'You');
  /** The "+" menu: who to ask about, adding a relative, and Deep answer. */
  protected readonly menuOpen = signal(false);
  protected readonly switching = signal(false);

  protected toggleDepth(): void {
    this.depthService.toggle();
  }
  protected choosePerson(): void {
    this.menuOpen.set(false);
    this.switching.set(true);
  }
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
