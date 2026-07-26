import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

/** A subject the reader can scope a question to. */
export interface AskTopic {
  id: string;
  label: string;
  icon: string;
}

/**
 * A prompt offered by the app, and why it is being offered.
 *
 * `because` is not decoration. A suggestion the reader cannot trace back to
 * something in their own chart is indistinguishable from an advert, and Epic J
 * requires that every reading be traceable to its basis.
 */
export interface AskSuggestion {
  prompt: string;
  because?: string;
}

/**
 * Ask — Home (Figma node 25:25).
 *
 * The blank prompt is the hardest screen in the app: a reader who does not
 * already know what astrology can answer will type nothing. Topics and
 * suggestions exist to make the first question cheap.
 *
 * The topic chips include Health and Money, and that is deliberate — the
 * product constraint is not that those subjects are unaskable, it is that
 * medical, legal and financial *verdicts* are never issued. A question in
 * either topic that asks for one is answered by the refer-out screen (27:83),
 * so the chips stay and the boundary is enforced where the answer is produced.
 */
@Component({
  selector: 'as-ask-home',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './ask-home.component.html',
  styleUrl: './ask-home.component.scss',
})
export class AskHomeComponent {
  readonly name = signal('Lakshmi');
  protected readonly heading = computed(() => `What’s on your mind, ${this.name()}?`);

  readonly topics = signal<AskTopic[]>([
    { id: 'work', label: 'Work', icon: 'topic-work' },
    { id: 'marriage', label: 'Marriage', icon: 'topic-marriage' },
    { id: 'money', label: 'Money', icon: 'topic-money' },
    { id: 'child', label: 'My child', icon: 'topic-child' },
    { id: 'health', label: 'Health', icon: 'topic-health' },
  ]);

  readonly selectedTopic = signal<string | null>(null);

  /**
   * Seeded from the chart and the day, per the design's own heading — "right
   * now" is a claim, so these have to move when the dasha or the transit does.
   */
  readonly suggestions = signal<AskSuggestion[]>([
    { prompt: 'Your Saturn period is active — ask about work & patience' },
    { prompt: 'Moon is in Hasta today — good for detail work' },
    { prompt: 'Is this month good for a big purchase?' },
  ]);

  /**
   * The composer, pre-filled from `?q=` when the reader arrived by tapping a
   * suggestion on Today. Pre-filled rather than sent: the suggestion is the
   * app's wording, and the reader gets to edit it before it becomes their
   * question.
   *
   * Read from the snapshot rather than the observable: it is a handoff at
   * entry, and re-reading would overwrite whatever the reader had started
   * typing.
   */
  readonly draft = signal(inject(ActivatedRoute).snapshot.queryParamMap.get('q') ?? '');

  protected toggleTopic(id: string): void {
    this.selectedTopic.update((current) => (current === id ? null : id));
  }
}
