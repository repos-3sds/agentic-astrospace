import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { NgTemplateOutlet } from '@angular/common';
import { ASK_NAVIGATION } from './ask-navigation';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AskComposerComponent } from './ask-composer.component';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { FIND_A_HELPLINE, crisisSupportFor } from '../../../core/crisis-support';
import { PreferencesService } from '../../../core/preferences.service';

/** The domains the app declines to give a verdict in, and the crisis reply. */
export type ReferDomain = 'health' | 'legal' | 'money' | 'death' | 'crisis';

/** What the refer-out says, per domain. */
interface ReferCopy {
  /** Who this actually belongs to. */
  headline: string;
  boundary: string;
  offer: string;
  /** The one thing the app will still do. Omitted where nothing is on offer. */
  action?: string;
  /**
   * Where the offer goes. The health and legal/money offers land on the
   * remedies list and the day's timings respectively — both are things the app
   * *can* do, which is the point of offering them beside a refusal.
   */
  actionRoute?: string[];
}

const COPY: Record<ReferDomain, ReferCopy> = {
  health: {
    headline: 'This needs a real doctor, not an app',
    boundary:
      'This guide never diagnoses illness or predicts health outcomes — that call belongs to a qualified doctor. Please reach out to one if this is troubling you; please don’t wait on an app for something this important.',
    offer:
      'A gentle daily check-in, and — if it helps — a traditional wellbeing practice for this period. Never a substitute for medical care.',
    action: 'See a wellbeing practice',
    actionRoute: ['/m', 'remedies'],
  },
  legal: {
    headline: 'This needs a lawyer, not an app',
    boundary:
      'This guide never predicts how a case will end or what a court will decide — that call belongs to a qualified lawyer. Please talk to one before you act on anything here.',
    offer:
      'Timing for the steps around it — when to have the conversation, when to file, which mornings are steadier. Never advice on the matter itself.',
    action: 'See timing for this week',
    actionRoute: ['/m', 'muhurta'],
  },
  money: {
    headline: 'This needs a financial adviser, not an app',
    boundary:
      'This guide never tells you what to buy, sell or invest in, and never predicts what a market will do — that call belongs to a qualified adviser, and to you.',
    offer:
      'Timing for decisions you have already made — which days are steadier for a conversation or a signature. Never a view on the decision itself.',
    action: 'See timing for this week',
    actionRoute: ['/m', 'muhurta'],
  },
  death: {
    headline: 'This is not something we will answer',
    boundary:
      'This guide does not predict death or lifespan, for anyone, ever. Classical texts contain such methods; we do not use them, because no one is served by a date they cannot check and cannot unhear.',
    offer:
      'If you are worried about someone’s health, a doctor can actually help. If you are carrying something heavier than that, please talk to someone you trust, or call one of the free lines below.',
  },
  // Not a boundary: the reader may be in danger. Warm, short, and the
  // numbers first (safety.py "crisis", sweep 2026-10-29 G-1).
  crisis: {
    headline: 'You don’t have to carry this alone',
    boundary:
      'Thank you for telling me. What you are feeling matters, and it can ease. A trained listener is ready to hear you right now, free and in confidence.',
    offer:
      'Take one slow breath. Call one of these lines when you are ready, or tell someone you trust what you told me. You are not a burden for reaching out.',
  },
};

/**
 * Ask — Refer-out (Figma node 27:83), routed at /m/ask/refer.
 *
 * This screen is the product constraint made visible: no death, longevity, or
 * medical, legal or financial verdicts — those refer out to a qualified
 * professional instead of being answered. It is deliberately not an error
 * state. The question was a reasonable one to ask; the app is the wrong place
 * to ask it, and saying so plainly is more use than a hedged non-answer.
 *
 * Gold, not the warn colour: warn marks a window the reading is telling you to
 * avoid, and this is the app declining to read at all.
 *
 * The standing-policy line at the foot is not filler. A boundary that only
 * appears when you personally hit it reads as a judgement about your question;
 * saying it holds for everyone, always, is what stops it feeling like one.
 */
@Component({
  selector: 'as-ask-refer-out',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [AskComposerComponent, RouterLink, BackLinkDirective, NgTemplateOutlet],
  templateUrl: './ask-refer-out.component.html',
  styleUrl: './ask-refer-out.component.scss',
})
export class AskReferOutComponent {
  protected readonly navigation = inject(ASK_NAVIGATION);
  private readonly params = toSignal(inject(ActivatedRoute).queryParamMap, {
    requireSync: true,
  });

  protected readonly question = computed(
    () => this.params().get('q') ?? 'Will I recover from this illness?',
  );

  protected readonly domain = computed<ReferDomain>(() => {
    const asked = this.params().get('domain');
    return asked && asked in COPY ? (asked as ReferDomain) : 'health';
  });

  protected readonly copy = computed(() => COPY[this.domain()]);

  /** Helplines for where the phone is now, shown with the crisis and death replies. */
  protected readonly support = crisisSupportFor(inject(PreferencesService).browserTimezone());
  protected readonly findHelpline = FIND_A_HELPLINE;

  readonly draft = signal('');

  private readonly router = inject(Router);

  protected askAgain(question: string): void {
    void this.router.navigate(this.navigation.path(), { queryParams: { q: question } });
    this.draft.set('');
  }
}
