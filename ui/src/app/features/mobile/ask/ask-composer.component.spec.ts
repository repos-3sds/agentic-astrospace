import { TestBed } from '@angular/core/testing';
import { AskComposerComponent } from './ask-composer.component';
import { ASK_NAVIGATION } from './ask-navigation';

describe('Ask composer host isolation', () => {
  it('preserves the mobile input and Enter submission by default', () => {
    const fixture = TestBed.createComponent(AskComposerComponent);
    fixture.componentRef.setInput('value', 'A question');
    fixture.detectChanges();
    const submit = spyOn(fixture.componentInstance.submitted, 'emit');
    expect(fixture.nativeElement.querySelector('textarea')).toBeNull();
    fixture.nativeElement.querySelector('input').dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    expect(submit).toHaveBeenCalledWith('A question');
    expect(fixture.nativeElement.classList.contains('web-composer')).toBeFalse();
  });

  it('uses multiline input only on web; Shift+Enter and IME do not submit', () => {
    TestBed.configureTestingModule({ providers: [{ provide: ASK_NAVIGATION, useValue: { web: true } }] });
    const fixture = TestBed.createComponent(AskComposerComponent);
    fixture.componentRef.setInput('value', 'A question');
    fixture.detectChanges();
    const submit = spyOn(fixture.componentInstance.submitted, 'emit');
    expect(fixture.nativeElement.querySelector('input')).toBeNull();
    const field = fixture.nativeElement.querySelector('textarea');
    field.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true }));
    field.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', isComposing: true }));
    expect(submit).not.toHaveBeenCalled();
    field.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    expect(submit).toHaveBeenCalledOnceWith('A question');
  });

  it('focus() puts the caret after a pre-filled suggestion', async () => {
    const fixture = TestBed.createComponent(AskComposerComponent);
    fixture.componentRef.setInput('value', 'What should I focus on at work?');
    fixture.detectChanges();
    document.body.appendChild(fixture.nativeElement);
    fixture.componentInstance.focus();
    await new Promise((resolve) => requestAnimationFrame(() => resolve(null)));
    const field: HTMLInputElement = fixture.nativeElement.querySelector('input');
    expect(document.activeElement).toBe(field);
    expect(field.selectionStart).toBe(field.value.length);
    fixture.nativeElement.remove();
  });
});
