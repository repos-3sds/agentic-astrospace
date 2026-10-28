import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { AskWeighing, AskWeighingAngle } from '../../../core/models';

type CallTone = 'good' | 'even' | 'warn' | 'bad';

const CALL_WORDS: Record<string, string> = {
  good: 'Good',
  moderate: 'Fairly good',
  neutral: 'Neutral',
  mixed: 'Mixed',
  weak: 'Weak',
  bad: 'Against',
};

const CALL_TONES: Record<string, CallTone> = {
  good: 'good',
  moderate: 'good',
  neutral: 'even',
  mixed: 'even',
  weak: 'warn',
  bad: 'bad',
};

/**
 * "How we weighed it": every point of view the tool-using Ask judged, how much
 * it counts, and the combined call. Guided readers get plain names and no
 * reasons (the reasons carry chart terms); Balanced and Practitioner see both.
 */
@Component({
  selector: 'as-ask-weighing-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './ask-weighing-card.component.scss',
  template: `
    <section class="answer-section weighing-card" aria-label="How we weighed it">
      <header>
        <h2>How we weighed it</h2>
        <p class="weighing-sub">
          {{ plain() ? 'Each part of your chart, how much it counts, and what it says.' : 'Each point of view, its weight (1 to 5), and its call.' }}
        </p>
      </header>
      <ol class="angle-list">
        @for (angle of angles(); track angle.key) {
          <li class="angle-row">
            <div class="angle-head">
              <span class="angle-name">{{ name(angle) }}</span>
              <span class="call-pill" [attr.data-tone]="tone(angle.call)">{{ callWord(angle.call) }}</span>
            </div>
            <span class="weight" role="img" [attr.aria-label]="'Weight ' + angle.weight + ' of 5'">
              @for (dot of dots; track dot) {
                <span class="dot" [class.on]="dot <= angle.weight"></span>
              }
            </span>
            @if (!plain() && angle.why) {
              <p class="angle-why">{{ angle.why }}</p>
            }
          </li>
        }
      </ol>
      <div class="overall" [attr.data-tone]="bandTone()">
        <span class="overall-label">{{ plain() ? 'All together' : 'Overall' }}</span>
        <strong class="overall-band">{{ bandWord() }}</strong>
      </div>
    </section>
  `,
})
export class AskWeighingCardComponent {
  readonly weighing = input.required<AskWeighing>();
  /** Guided mode: plain names, no chart reasons. */
  readonly plain = input(false);

  protected readonly dots = [1, 2, 3, 4, 5];

  /** Heaviest first, so the reader sees what counted most at the top. */
  protected readonly angles = computed(() =>
    [...(this.weighing().angles ?? [])].sort((a, b) => b.weight - a.weight),
  );

  protected readonly bandWord = computed(() => {
    const band = this.weighing().overall?.band ?? '';
    return band ? band.charAt(0).toUpperCase() + band.slice(1) : '';
  });

  protected readonly bandTone = computed<CallTone>(() => {
    const band = this.weighing().overall?.band ?? '';
    if (band.startsWith('good') || band.startsWith('moderately')) return 'good';
    if (band.startsWith('weak')) return 'warn';
    if (band.startsWith('unfavourable')) return 'bad';
    return 'even';
  });

  protected name(angle: AskWeighingAngle): string {
    return this.plain() ? angle.plain_label || angle.label : angle.label;
  }

  protected callWord(call: string): string {
    return CALL_WORDS[call] ?? call;
  }

  protected tone(call: string): CallTone {
    return CALL_TONES[call] ?? 'even';
  }
}
