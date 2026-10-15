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
        <header id="head"><h2>Day quality</h2></header>
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

  /** The sheet slides out (animate.leave) before Angular removes it. */
  async function removed(): Promise<boolean> {
    const deadline = performance.now() + 1500;
    while (performance.now() < deadline) {
      fixture.detectChanges();
      if (!fixture.nativeElement.querySelector('as-sheet')) return true;
      await new Promise((resolve) => setTimeout(resolve, 20));
    }
    return false;
  }

  function pointer(target: Element, type: string, clientY: number): void {
    target.dispatchEvent(new PointerEvent(type, {
      pointerId: 7, button: 0, clientY, bubbles: true, cancelable: true, pointerType: 'touch',
    }));
  }

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

  it('offers a visible 44 px Close control that dismisses', async () => {
    openSheet();
    const close = fixture.nativeElement.querySelector('.close') as HTMLButtonElement;
    expect(close.getAttribute('aria-label')).toBe('Close');
    expect(getComputedStyle(close).width).toBe('44px');
    close.click();
    fixture.detectChanges();
    expect(await removed()).toBeTrue();
  });

  it('dismisses when the header is dragged down past the threshold', async () => {
    const panel = openSheet();
    const head = panel.querySelector('#head')!;
    pointer(head, 'pointerdown', 100);
    pointer(panel, 'pointermove', 180);
    expect(panel.style.transform).toBe('translateY(80px)');
    pointer(panel, 'pointermove', 260);
    pointer(panel, 'pointerup', 260);
    fixture.detectChanges();
    expect(await removed()).toBeTrue();
  });

  it('springs back from a short drag on the handle', () => {
    const panel = openSheet();
    const handle = panel.querySelector('.handle')!;
    pointer(handle, 'pointerdown', 100);
    pointer(panel, 'pointermove', 130);
    pointer(panel, 'pointerup', 130);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('as-sheet')).not.toBeNull();
    expect(panel.style.transform).toBe('');
  });

  it('does not start a drag from a control inside the header row', () => {
    const panel = openSheet();
    const close = panel.querySelector('.close')!;
    pointer(close, 'pointerdown', 100);
    pointer(panel, 'pointermove', 300);
    expect(panel.style.transform).toBe('');
  });

  it('keeps scrolling inside the sheet from chaining to the page', () => {
    const panel = openSheet();
    expect(getComputedStyle(panel).overscrollBehaviorY).toBe('contain');
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

  it('closes on Escape and returns focus to the opener', async () => {
    const panel = openSheet();
    key(panel, 'Escape');
    fixture.detectChanges();
    expect(await removed()).toBeTrue();
    expect(document.activeElement).toBe(fixture.nativeElement.querySelector('#opener'));
  });
});

/** TestBed disables animate.leave by default; this block turns it back on. */
describe('SheetComponent exit', () => {
  it('slides out before it is removed, instead of vanishing in one frame', async () => {
    await TestBed.configureTestingModule({ imports: [HostComponent], animationsEnabled: true }).compileComponents();
    const fixture = TestBed.createComponent(HostComponent);
    document.body.appendChild(fixture.nativeElement);
    fixture.detectChanges();
    fixture.componentInstance.open.set(true);
    fixture.detectChanges();
    (fixture.nativeElement.querySelector('.close') as HTMLButtonElement).click();
    fixture.detectChanges();
    await new Promise((resolve) => setTimeout(resolve, 40));

    const host = fixture.nativeElement.querySelector('as-sheet') as HTMLElement | null;
    expect(host).not.toBeNull();
    expect(host!.classList).toContain('is-leaving');
    expect((host!.querySelector('.panel') as HTMLElement).style.transform).toBe('translateY(100%)');

    await new Promise((resolve) => setTimeout(resolve, 500));
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('as-sheet')).toBeNull();
    fixture.nativeElement.remove();
  });
});
