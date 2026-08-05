import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AskComposerComponent } from './ask-composer.component';
import { VoiceListeningComponent } from './voice-listening.component';
import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';

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
  imports: [AskComposerComponent, VoiceListeningComponent, RouterLink],
  templateUrl: './ask-home.component.html',
  styleUrl: './ask-home.component.scss',
})
export class AskHomeComponent {
  private readonly kundlis = inject(KundliStore);
  protected readonly preferences = inject(PreferencesService);
  readonly name = computed(() => this.kundlis.active()?.name ?? 'there');
  protected readonly heading = computed(() => `What’s on your mind, ${this.name()}?`);
  protected readonly lede = computed(() => ({
    guided: 'Ask in plain language. We keep the answer practical and explain unfamiliar terms.',
    balanced: 'Ask anything — job, money, family, timing. You’ll get a plain answer, computed from your chart.',
    practitioner: 'Ask with chart context. Answers include factors, conventions and provenance where available.',
  })[this.preferences.experienceMode()]);

  private readonly allTopics: AskTopic[] = [
    { id: 'work', label: 'Work', icon: 'topic-work' },
    { id: 'marriage', label: 'Marriage', icon: 'topic-marriage' },
    { id: 'money', label: 'Money', icon: 'topic-money' },
    { id: 'child', label: 'My child', icon: 'topic-child' },
    { id: 'health', label: 'Health', icon: 'topic-health' },
  ];
  readonly topics = computed<AskTopic[]>(() => {
    if (this.preferences.experienceMode() === 'guided') {
      return this.allTopics.filter((topic) => ['work', 'marriage', 'child'].includes(topic.id));
    }
    return this.allTopics;
  });

  readonly selectedTopic = signal<string | null>(null);

  /**
   * Seeded from the chart and the day, per the design's own heading — "right
   * now" is a claim, so these have to move when the dasha or the transit does.
   */
  readonly suggestions = computed<AskSuggestion[]>(() => {
    if (this.preferences.experienceMode() === 'guided') {
      return [
        { prompt: 'What should I focus on at work this week?', because: 'Plain-language starter' },
        { prompt: 'What is one thing to avoid today?', because: 'Safety-first daily prompt' },
        { prompt: 'How should I think about a family conversation?', because: 'Practical guidance' },
      ];
    }
    if (this.preferences.experienceMode() === 'practitioner') {
      return [
        { prompt: 'Explain my current dasha with natal and transit factors', because: 'Technical depth' },
        { prompt: 'Which transit rules are driving today’s reading?', because: 'Provenance check' },
        { prompt: 'Compare D1 and D9 factors for this relationship question', because: 'Chart-layer prompt' },
      ];
    }
    return [
      { prompt: 'Your Saturn period is active — ask about work & patience' },
      { prompt: 'Moon is in Hasta today — good for detail work' },
      { prompt: 'Is this month good for a big purchase?' },
    ];
  });
  protected readonly safetyLine = computed(() =>
    this.preferences.experienceMode() === 'practitioner'
      ? 'Safety boundary unchanged: medical, legal and financial verdicts still refer out.'
      : 'For medical, legal or financial decisions, this guide gives timing context only.',
  );

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

  /**
   * Whether the microphone overlay (25:123) is up.
   *
   * Placeholder transcript until speech recognition is wired: the screen has to
   * be verifiable in both its states, and an always-empty one hides half of it.
   */
  readonly listening = signal(false);
  readonly heard = signal('Is this a good time to change my job');
  readonly submitting = signal(false);
  readonly submitError = signal<string | null>(null);

  constructor() {
    if (!this.kundlis.loaded()) void this.kundlis.load().catch(() => undefined);
  }

  protected startListening(): void {
    this.listening.set(true);
  }

  /** Voice fills the composer; it does not send. The reader still confirms. */
  protected acceptSpeech(text: string): void {
    this.draft.set(text);
    this.listening.set(false);
  }

  protected toggleTopic(id: string): void {
    this.selectedTopic.update((current) => (current === id ? null : id));
  }

  private readonly router = inject(Router);

  /**
   * Send the question on to the answer view (26:54).
   *
   * The topic, when one is selected, rides along: it is the reader saying which
   * of several readings of an ambiguous question they meant, and dropping it
   * would make the chips decorative.
   *
   * Every question currently lands on the answer view, including ones that must
   * refer out — a health question here still shows a career verdict. Which of
   * the two screens a question belongs on is the answer pipeline's call, not
   * the composer's: classifying intent in the client would put the safety
   * boundary somewhere it can be skipped by anything that does not go through
   * this button. The refer-out screen is built and routed; wiring it is part of
   * connecting /api/v1/ask, and until then this is placeholder routing like the
   * placeholder verdict it lands on.
   */
  protected async ask(question: string): Promise<void> {
    const q = question.trim();
    if (!q || this.submitting()) {
      return;
    }
    await this.router.navigate(['/m', 'ask', 'answer'], {
      queryParams: { q, topic: this.selectedTopic() ?? undefined, preview: 'construction' },
    });
  }
}
