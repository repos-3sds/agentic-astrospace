import { TestBed } from '@angular/core/testing';

import { ReportAnswerSheetComponent } from './report-answer-sheet.component';
import { MobileAskThreadService } from './mobile-ask-thread.service';

/** "Report this answer" (Google Play's rule for AI-generated content). */
describe('ReportAnswerSheetComponent', () => {
  let report: jasmine.Spy;

  function render() {
    report = jasmine.createSpy('report').and.resolveTo(undefined);
    TestBed.configureTestingModule({
      imports: [ReportAnswerSheetComponent],
      providers: [{ provide: MobileAskThreadService, useValue: { report } }],
    });
    const fixture = TestBed.createComponent(ReportAnswerSheetComponent);
    fixture.componentRef.setInput('context', {
      answer: 'A steady year at work.', question: 'Will my job change?',
      thread_id: 't1', message_id: 'm1', experience_mode: 'guided', language: 'en',
    });
    document.body.appendChild(fixture.nativeElement);
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => {
    document.querySelectorAll('as-report-answer-sheet').forEach((el) => el.remove());
    TestBed.resetTestingModule();
  });

  it('offers five plain reasons and waits for one before sending', () => {
    const fixture = render();
    const el: HTMLElement = fixture.nativeElement;
    const reasons = [...el.querySelectorAll('[role="radio"] .reason-label')].map((r) => r.textContent?.trim());
    expect(reasons).toEqual([
      'Wrong or made up', 'Harmful or frightening', 'Rude or offensive',
      'Health, legal or money advice', 'Something else',
    ]);
    expect((el.querySelector('.send') as HTMLButtonElement).disabled).toBeTrue();
  });

  it('sends the reason, a trimmed note and the answer, then says thank you', async () => {
    const fixture = render();
    const el: HTMLElement = fixture.nativeElement;
    let reported = 0;
    fixture.componentInstance.reported.subscribe(() => reported++);
    (el.querySelectorAll('[role="radio"]')[1] as HTMLButtonElement).click();
    const note = el.querySelector('textarea') as HTMLTextAreaElement;
    note.value = '  It scared my mother.  ';
    note.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    expect(el.querySelectorAll('[role="radio"]')[1].getAttribute('aria-checked')).toBe('true');
    (el.querySelector('.send') as HTMLButtonElement).click();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(report).toHaveBeenCalledWith(jasmine.objectContaining({
      reason: 'harmful', note: 'It scared my mother.', answer: 'A steady year at work.',
      thread_id: 't1', message_id: 'm1',
    }));
    expect(reported).toBe(1);
    expect(el.textContent).toContain('Thank you');
  });

  it('keeps the sheet open with the reason when sending fails', async () => {
    const fixture = render();
    report.and.rejectWith(new Error('No connection. Please try again.'));
    const el: HTMLElement = fixture.nativeElement;
    (el.querySelectorAll('[role="radio"]')[0] as HTMLButtonElement).click();
    fixture.detectChanges();
    (el.querySelector('.send') as HTMLButtonElement).click();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(el.querySelector('[role="alert"]')?.textContent).toContain('No connection');
    expect(el.querySelectorAll('[role="radio"]')[0].getAttribute('aria-checked')).toBe('true');
  });
});
