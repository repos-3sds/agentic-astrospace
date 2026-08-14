import { computed, importProvidersFrom, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { LucideAngularModule, BadgeAlert, CircleAlert, MessageCircle, Send, Sparkles } from 'lucide-angular';

import { AskTabComponent } from './ask-tab.component';
import { AskService } from '../../../core/ask.service';
import { KundliStore } from '../../../core/kundli.store';
import { AskMessage } from '../../../core/models';

/**
 * 2026-08-14, PR #53 follow-up: the web Ask endpoint started returning an
 * explicit `status` (Codex review finding — see ask.service.spec.ts for the
 * service-level half of this fix), but nothing proved the component actually
 * renders a `domain_not_ready`/`clarification_needed` reply differently from
 * a real answered one. Rendering both into the same generic `.bubble.assistant`
 * would let a refusal or an unsupported-domain notice look exactly like a
 * grounded reading. This renders the real template and asserts on the DOM.
 */
function createFixture(messages: AskMessage[]) {
  const kundlis = [{ id: 'k1', name: 'Test Chart' }];
  const store = {
    kundlis: signal(kundlis as any),
    activeId: signal<string | null>('k1'),
    active: computed(() => kundlis[0] as any),
  };
  const history = signal<AskMessage[]>(messages);
  const ask = {
    history: () => history,
    pending: signal(false),
    ask: jasmine.createSpy(),
  };

  TestBed.configureTestingModule({
    imports: [AskTabComponent],
    providers: [
      provideNoopAnimations(),
      { provide: KundliStore, useValue: store },
      { provide: AskService, useValue: ask },
      importProvidersFrom(
        LucideAngularModule.pick({ BadgeAlert, CircleAlert, MessageCircle, Send, Sparkles }),
      ),
    ],
  });
  const fixture = TestBed.createComponent(AskTabComponent);
  fixture.detectChanges();
  return fixture;
}

describe('AskTabComponent boundary-state rendering', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('renders an answered reply as an ordinary assistant bubble', () => {
    const fixture = createFixture([
      { role: 'user', content: 'What does my chart say about my career?' },
      { role: 'assistant', content: 'Your 10th house is strong.', status: 'answered', tools: ['get_birth_chart'] },
    ]);
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.bubble.assistant.boundary')).toBeNull();
    expect(el.querySelector('.bubble.assistant')?.textContent).toContain('Your 10th house is strong.');
  });

  it('never renders a domain_not_ready reply as the ordinary answered bubble', () => {
    const fixture = createFixture([
      { role: 'user', content: 'Will I win my court case?' },
      {
        role: 'assistant',
        content: "Litigation isn't ready yet. I can currently help with: career, marriage.",
        status: 'domain_not_ready',
      },
    ]);
    const el: HTMLElement = fixture.nativeElement;
    const boundary = el.querySelector('.bubble.assistant.boundary');
    expect(boundary).not.toBeNull();
    expect(boundary?.classList.contains('refer-out')).toBeFalse();
    expect(boundary?.textContent).toContain("Litigation isn't ready yet");
    // The plain-answer path (with tool chips) must never also match.
    expect(el.querySelectorAll('.bubble.assistant').length).toBe(1);
  });

  it('never renders a clarification_needed reply as the ordinary answered bubble', () => {
    const fixture = createFixture([
      { role: 'user', content: 'Tell me about it' },
      {
        role: 'assistant',
        content: 'I can help with: career, marriage right now — which one is this about?',
        status: 'clarification_needed',
      },
    ]);
    const el: HTMLElement = fixture.nativeElement;
    const boundary = el.querySelector('.bubble.assistant.boundary');
    expect(boundary).not.toBeNull();
    expect(boundary?.classList.contains('refer-out')).toBeFalse();
  });

  it('renders context_unavailable as a retryable notice rather than an answer', () => {
    const fixture = createFixture([
      { role: 'user', content: 'When did my career begin?' },
      {
        role: 'assistant',
        content: 'I could not check your saved profile context just now. Please try again.',
        status: 'context_unavailable',
      },
    ]);
    const el: HTMLElement = fixture.nativeElement;
    const boundary = el.querySelector('.bubble.assistant.boundary');
    expect(boundary).not.toBeNull();
    expect(boundary?.classList.contains('refer-out')).toBeFalse();
    expect(boundary?.textContent).toContain('saved profile context');
  });

  it('renders a refer_out reply with the stronger refer-out treatment', () => {
    const fixture = createFixture([
      { role: 'user', content: 'Do I have a fatal illness coming?' },
      {
        role: 'assistant',
        content: 'That falls outside what I can responsibly speak to.',
        status: 'refer_out',
        refer_out_kind: 'health',
      },
    ]);
    const el: HTMLElement = fixture.nativeElement;
    const boundary = el.querySelector('.bubble.assistant.boundary');
    expect(boundary).not.toBeNull();
    expect(boundary?.classList.contains('refer-out')).toBeTrue();
  });

  it('treats a pre-status assistant message (no `status` field) as an ordinary answer', () => {
    const fixture = createFixture([
      { role: 'user', content: 'Old thread question' },
      { role: 'assistant', content: 'An answer from before the status field existed.' },
    ]);
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.bubble.assistant.boundary')).toBeNull();
  });
});
