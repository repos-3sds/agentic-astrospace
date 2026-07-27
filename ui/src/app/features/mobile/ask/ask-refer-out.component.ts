import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AskComposerComponent } from './ask-composer.component';

/** The domains the app declines to give a verdict in. */
export type ReferDomain = 'health' | 'legal' | 'money' | 'death';

/** What the refer-out says, per domain. */
interface ReferCopy {
  /** Who this actually belongs to. */
  headline: string;
  boundary: string;
  offer: string;
  /** The one thing the app will still do. Omitted where nothing is on offer. */
  action?: string;
}

const COPY: Record<ReferDomain, ReferCopy> = {
  health: {
    headline: 'This needs a real doctor, not an app',
    boundary:
      'AstroSpace never diagnoses illness or predicts health outcomes — that call belongs to a qualified doctor. Please reach out to one if this is troubling you; please don’t wait on an app for something this important.',
    offer:
      'A gentle daily check-in, and — if it helps — a traditional wellbeing practice for this period. Never a substitute for medical care.',
    action: 'See a wellbeing practice',
  },
  legal: {
    headline: 'This needs a lawyer, not an app',
    boundary:
      'AstroSpace never predicts how a case will end or what a court will decide — that call belongs to a qualified lawyer. Please talk to one before you act on anything here.',
    offer:
      'Timing for the steps around it — when to have the conversation, when to file, which mornings are steadier. Never advice on the matter itself.',
    action: 'See timing for this week',
  },
  money: {
    headline: 'This needs a financial adviser, not an app',
    boundary:
      'AstroSpace never tells you what to buy, sell or invest in, and never predicts what a market will do — that call belongs to a qualified adviser, and to you.',
    offer:
      'Timing for decisions you have already made — which days are steadier for a conversation or a signature. Never a view on the decision itself.',
    action: 'See timing for this week',
  },
  death: {
    headline: 'This is not something we will answer',
    boundary:
      'AstroSpace does not predict death or lifespan, for anyone, ever. Classical texts contain such methods; we do not use them, because no one is served by a date they cannot check and cannot unhear.',
    offer:
      'If you are worried about someone’s health, a doctor can actually help. If you are carrying something heavier than that, please talk to someone you trust.',
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
  imports: [AskComposerComponent, RouterLink],
  templateUrl: './ask-refer-out.component.html',
  styleUrl: './ask-refer-out.component.scss',
})
export class AskReferOutComponent {
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

  readonly draft = signal('');

  private readonly router = inject(Router);

  protected askAgain(question: string): void {
    void this.router.navigate(['/m', 'ask'], { queryParams: { q: question } });
    this.draft.set('');
  }
}
