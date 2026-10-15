import { Component, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SheetComponent } from './sheet.component';

@Component({
  standalone: true,
  imports: [SheetComponent],
  template: `
    <button id="opener" type="button" (click)="open.set(true)">Open</button>
    @if (open()) {
      <as-sheet (dismissed)="open.set(false)">
        <h2>Day quality</h2>
        <p>Some detail.</p>
        <button id="first" type="button">First</button>
        <button id="last" type="button">Last</button>
      </as-sheet>
    }
  `,
})
class HostComponent {
  readonly open = signal(false);
}

/**
 * Until 2026-10-15 a sheet had role=dialog and aria-modal but nothing ever
 * took focus, Tab wandered into the page underneath, the dialog had no name,
 * and the only dismissal for anyone not using touch was an aria-hidden scrim.
 */
describe('SheetComponent accessibility', () => {
  let fixture: ComponentFixture<HostComponent>;

  function key(target: Element, key: string, shiftKey = false): KeyboardEvent {
    const event = new KeyboardEvent('keydown', { key, shiftKey, bubbles: true, cancelable: true });
    target.dispatchEvent(event);
    return event;
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    document.body.appendChild(fixture.nativeElement);
    fixture.detectChanges();
  });

  afterEach(() => fixture.nativeElement.remove());

  function openSheet(): HTMLElement {
    const opener = fixture.nativeElement.querySelector('#opener') as HTMLButtonElement;
    opener.focus();
    opener.click();
    fixture.detectChanges();
    return fixture.nativeElement.querySelector('.panel') as HTMLElement;
  }

  it('moves focus into the panel and names the dialog by its first heading', () => {
    const panel = openSheet();
    expect(document.activeElement).toBe(panel);
    const heading = panel.querySelector('h2')!;
    expect(heading.id).toContain('as-sheet-title-');
    expect(panel.getAttribute('aria-labelledby')).toBe(heading.id);
    expect(panel.hasAttribute('aria-label')).toBeFalse();
  });

  it('offers a visible 44 px Close control that dismisses', () => {
    openSheet();
    const close = fixture.nativeElement.querySelector('.close') as HTMLButtonElement;
    expect(close.getAttribute('aria-label')).toBe('Close');
    expect(getComputedStyle(close).width).toBe('44px');
    close.click();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('as-sheet')).toBeNull();
  });

  it('keeps Tab inside the panel in both directions', () => {
    const panel = openSheet();
    const close = panel.querySelector('.close') as HTMLElement;
    const last = panel.querySelector('#last') as HTMLElement;

    const back = key(panel, 'Tab', true);
    expect(back.defaultPrevented).toBeTrue();
    expect(document.activeElement).toBe(last);

    last.focus();
    const forward = key(last, 'Tab');
    expect(forward.defaultPrevented).toBeTrue();
    expect(document.activeElement).toBe(close);
  });

  it('closes on Escape and returns focus to the opener', () => {
    const panel = openSheet();
    key(panel, 'Escape');
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('as-sheet')).toBeNull();
    expect(document.activeElement).toBe(fixture.nativeElement.querySelector('#opener'));
  });
});
