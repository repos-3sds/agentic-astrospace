import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { HapticsService } from '../../../core/haptics.service';
import { PullRefreshService } from '../../../core/pull-refresh.service';
import { SheetOverlayService } from '../../../core/sheet-overlay.service';
import { PULL_THRESHOLD, PullRefreshDirective } from './pull-refresh.directive';

@Component({
  standalone: true,
  imports: [PullRefreshDirective],
  template: `<div class="shell"><main class="content" asPullRefresh style="height:200px;overflow:auto"><div style="height:2000px"></div></main></div>`,
})
class HostComponent {}

function touch(target: HTMLElement, type: string, x: number, y: number): void {
  const point = new Touch({ identifier: 1, target, clientX: x, clientY: y });
  target.dispatchEvent(new TouchEvent(type, {
    touches: type === 'touchend' ? [] : [point],
    changedTouches: [point],
    bubbles: true,
  }));
}

function pull(el: HTMLElement, dx: number, dy: number, release = true): void {
  touch(el, 'touchstart', 100, 100);
  touch(el, 'touchmove', 100 + dx / 4, 100 + dy / 4);
  touch(el, 'touchmove', 100 + dx, 100 + dy);
  if (release) touch(el, 'touchend', 100 + dx, 100 + dy);
}

describe('PullRefreshDirective', () => {
  let url: string;
  let sheetOpen: ReturnType<typeof signal<boolean>>;
  let registry: PullRefreshService;

  function render(): HTMLElement {
    const fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
    document.body.appendChild(fixture.nativeElement);
    return fixture.nativeElement.querySelector('main') as HTMLElement;
  }

  beforeEach(() => {
    url = '/m/today';
    sheetOpen = signal(false);
    TestBed.configureTestingModule({
      imports: [HostComponent],
      providers: [
        { provide: Router, useValue: { get url() { return url; } } },
        { provide: SheetOverlayService, useValue: { open: sheetOpen } },
        { provide: HapticsService, useValue: jasmine.createSpyObj('HapticsService', ['select']) },
      ],
    });
    registry = TestBed.inject(PullRefreshService);
  });

  it('runs the screen handler after a pull past the threshold, and shows the spinner meanwhile', async () => {
    let finish!: () => void;
    const handler = jasmine.createSpy('handler').and.returnValue(new Promise<void>((done) => { finish = done; }));
    registry.register('/m/today', handler);
    const el = render();

    pull(el, 0, (PULL_THRESHOLD / 0.5) + 20);

    expect(handler).toHaveBeenCalledTimes(1);
    const indicator = el.parentElement!.querySelector('.m-pull-refresh')!;
    expect(indicator.classList).toContain('is-spinning');
    finish();
    await new Promise((done) => setTimeout(done, 600));
    expect(indicator.classList).not.toContain('is-visible');
  });

  it('lets go without refreshing when the pull stops short', () => {
    const handler = jasmine.createSpy('handler').and.resolveTo();
    registry.register('/m/today', handler);
    const el = render();

    pull(el, 0, PULL_THRESHOLD);

    expect(handler).not.toHaveBeenCalled();
  });

  it('ignores sideways swipes, a scrolled page, an open sheet and screens with no handler', () => {
    const handler = jasmine.createSpy('handler').and.resolveTo();
    registry.register('/m/today', handler);
    const el = render();
    const far = (PULL_THRESHOLD / 0.5) + 40;

    pull(el, far, far / 2);
    el.scrollTop = 50;
    pull(el, 0, far);
    el.scrollTop = 0;
    sheetOpen.set(true);
    pull(el, 0, far);
    sheetOpen.set(false);
    url = '/m/explore';
    pull(el, 0, far);

    expect(handler).not.toHaveBeenCalled();
  });

  it('files handlers by path, so a retained tab keeps its own and query strings do not matter', () => {
    const today = jasmine.createSpy('today').and.resolveTo();
    const calendar = jasmine.createSpy('calendar').and.resolveTo();
    registry.register('/m/today', today);
    const unregister = registry.register('/m/calendar', calendar);

    expect(registry.handlerFor('/m/today?listen=1')).toBe(today);
    expect(registry.handlerFor('/m/calendar')).toBe(calendar);
    unregister();
    expect(registry.handlerFor('/m/calendar')).toBeNull();
    expect(registry.handlerFor('/m/today')).toBe(today);
  });
});
