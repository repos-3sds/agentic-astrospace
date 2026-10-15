import { ChangeDetectionStrategy, Component, computed, effect, inject, signal, viewChild } from '@angular/core';
import { ASK_NAVIGATION } from './ask-navigation';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AskComposerComponent } from './ask-composer.component';
import { VoiceListeningComponent } from './voice-listening.component';
import { KundliStore } from '../../../core/kundli.store';
import { DailyGuidancePayload } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { buildAskSuggestions } from './ask-suggestions';
import { PreferencesService } from '../../../core/preferences.service';
import { EntitlementService } from '../../../core/entitlement.service';
import { SpeechService } from '../../../core/speech.service';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { SelectHapticDirective } from '../shared/select-haptic.directive';

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
  imports: [AskComposerComponent, VoiceListeningComponent, RouterLink, BackLinkDirective, SelectHapticDirective],
  templateUrl: './ask-home.component.html',
  styleUrl: './ask-home.component.scss',
})
export class AskHomeComponent {
  protected readonly navigation = inject(ASK_NAVIGATION);
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  protected readonly preferences = inject(PreferencesService);
  private readonly entitlements = inject(EntitlementService);

  /**
   * "2 of 3 free answers left this month". Only once limits block: before
   * then a count would read as a wall that is not there.
   */
  protected readonly allowanceLine = computed(() => {
    const allowance = this.entitlements.askAllowance();
    if (!allowance?.enforced) return null;
    const plan = this.entitlements.current()?.access_tier === 'free' ? 'free ' : '';
    const credits = allowance.credits ? ` · ${allowance.credits} bought question${allowance.credits === 1 ? '' : 's'}` : '';
    return `${allowance.remaining} of ${allowance.limit} ${plan}answers left this month${credits}`;
  });
  private readonly router = inject(Router);
  readonly name = computed(() => this.kundlis.active()?.name ?? 'there');
  protected readonly heading = computed(() => this.navigation.web ? 'What would you like to explore?' : `What’s on your mind, ${this.name()}?`);
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
   *
   * Until 2026-10-15 the Balanced list was three fixed strings ("Your Saturn
   * period is active…", "Moon is in Hasta today…", "Is this month good for a
   * big purchase?") shown to every profile, every day — one of them invited
   * a financial-verdict refer-out. They now come from the same daily
   * guidance payload Today renders (cached per profile and Vedic day), one
   * per life area, each with the chart fact it rests on. When the payload
   * is not available yet the list falls back to neutral, non-claiming
   * prompts rather than fabricated ones.
   */
  private readonly daily = signal<DailyGuidancePayload | null>(null);
  readonly suggestions = computed<AskSuggestion[]>(() => {
    if (this.navigation.web) return [
      { prompt: 'What should I consider about my career right now?' },
      { prompt: 'Help me understand my current dasha' },
      { prompt: 'What does my chart say about relationships?' },
    ];
    return buildAskSuggestions(this.daily(), this.preferences.experienceMode());
  });
  protected readonly safetyLine = computed(() =>
    this.preferences.experienceMode() === 'practitioner'
      ? 'Safety boundary unchanged: medical, legal and financial verdicts still refer out.'
      : 'For medical, legal or financial decisions, this guide gives timing context only.',
  );

  /**
   * The composer, pre-filled from `?q=` when the reader arrived by tapping a
   * suggestion on Today or "Ask about this" on a reading. Pre-filled rather
   * than sent: the suggestion is the app's wording, and the reader gets to
   * edit it before it becomes their question.
   *
   * /m/ask is a retained tab, so the component outlives one visit. Reading
   * the snapshot once meant a second handoff was ignored and the composer
   * opened empty (production audit 2026-10-15, R5). Each `q` is taken from
   * the live query params instead, then removed from the URL (replaceUrl),
   * so returning to the tab or reloading never re-applies an old one over
   * what the reader has typed since.
   */
  readonly draft = signal('');

  /** Whether the microphone overlay (25:123) is up. The transcript inside it
   * comes live from {@link SpeechService}. */
  readonly listening = signal(false);
  protected readonly speech = inject(SpeechService);
  readonly submitting = signal(false);
  readonly submitError = signal<string | null>(null);

  constructor() {
    void this.entitlements.refresh();
    const route = inject(ActivatedRoute);
    route.queryParamMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const q = params.get('q');
      if (q === null) return;
      this.draft.set(q);
      void this.router.navigate([], {
        relativeTo: route,
        queryParams: { q: null },
        queryParamsHandling: 'merge',
        replaceUrl: true,
      });
    });
    if (!this.kundlis.loaded()) void this.kundlis.load().catch(() => undefined);
    // Re-seed whenever the active profile changes; the service caches per
    // profile and day, so a revisit costs no request.
    effect(() => {
      const id = this.kundlis.activeId();
      this.daily.set(null);
      if (!id || this.navigation.web) return;
      void this.vedic.dailyGuidance(id)
        .then((payload) => { if (this.kundlis.activeId() === id) this.daily.set(payload); })
        .catch(() => undefined);
    });
  }

  protected startListening(): void {
    this.listening.set(true);
    void this.speech.start(this.preferences.language());
  }

  protected stopListening(): void {
    void this.speech.stop();
    this.listening.set(false);
  }

  /** Voice fills the composer; it does not send. The reader still confirms. */
  protected acceptSpeech(text: string): void {
    void this.speech.stop();
    this.draft.set(text);
    this.listening.set(false);
  }

  private readonly composer = viewChild(AskComposerComponent);

  /**
   * A suggestion goes into the composer; it is not sent. Same as tapping one
   * on Today: the suggestion is the app's wording, and the reader gets to
   * edit it before it becomes their question. Sending on tap also opened a
   * new thread with the same title on every tap (flow audit 5.4).
   */
  protected useSuggestion(prompt: string): void {
    this.draft.set(prompt);
    this.composer()?.focus();
  }

  protected toggleTopic(id: string): void {
    this.selectedTopic.update((current) => (current === id ? null : id));
  }

  /**
   * Send the question on to the answer view (26:54), which owns the actual
   * call to the orchestrator (POST /ask/{kundliId}/stream) and streams the
   * answer in as it's asked to open.
   *
   * The topic, when one is selected, rides along: it is the reader saying which
   * of several readings of an ambiguous question they meant, and dropping it
   * would make the chips decorative.
   *
   * Every question lands on the answer view first, including ones that must
   * refer out — the answer view redirects to the refer-out screen itself once
   * the response comes back with a refer_out_kind. Which of the two screens a
   * question belongs on is the answer pipeline's call, not the composer's:
   * classifying intent in the client would put the safety boundary somewhere
   * it can be skipped by anything that does not go through this button.
   */
  protected async ask(question: string): Promise<void> {
    const q = question.trim();
    if (!q || this.submitting()) {
      return;
    }
    await this.router.navigate(this.navigation.path('answer'), {
      queryParams: { q, topic: this.selectedTopic() ?? undefined, pending: '1' },
    });
  }
}
