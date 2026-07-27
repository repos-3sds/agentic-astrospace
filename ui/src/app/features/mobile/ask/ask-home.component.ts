import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AskComposerComponent } from './ask-composer.component';
import { VoiceListeningComponent } from './voice-listening.component';
import { KundliStore } from '../../../core/kundli.store';
import { ApiService } from '../../../core/api.service';
import { AskResponse } from '../../../core/models';
import { MobileAskStateService } from './mobile-ask-state.service';

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
  imports: [AskComposerComponent, VoiceListeningComponent],
  templateUrl: './ask-home.component.html',
  styleUrl: './ask-home.component.scss',
})
export class AskHomeComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly api = inject(ApiService);
  private readonly askState = inject(MobileAskStateService);
  readonly name = computed(() => this.kundlis.active()?.name ?? 'there');
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
    this.submitting.set(true);
    this.submitError.set(null);
    try {
      await this.kundlis.load();
      const profile = this.kundlis.active();
      if (!profile) {
        this.submitError.set('Create a profile before asking a chart question.');
        return;
      }
      const response = await this.api.post<AskResponse>(`/ask/${profile.id}`, {
        question: q,
        start_thread: true,
        input_mode: 'text',
      });
      this.askState.remember(response);
      if (response.refer_out_kind) {
        await this.router.navigate(['/m', 'ask', 'refer'], {
          queryParams: {
            q,
            domain: response.refer_out_kind,
            thread: response.thread_id ?? undefined,
          },
        });
      } else {
        await this.router.navigate(['/m', 'ask', 'answer'], {
          queryParams: {
            q,
            thread: response.thread_id ?? undefined,
            topic: this.selectedTopic() ?? undefined,
          },
        });
      }
    } catch (error) {
      this.submitError.set((error as Error).message);
    } finally {
      this.submitting.set(false);
    }
  }
}
