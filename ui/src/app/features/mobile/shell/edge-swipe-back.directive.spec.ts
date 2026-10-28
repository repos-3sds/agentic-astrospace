import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { NativeBackService } from '../../../core/native-back.service';
import { EdgeSwipeBackDirective } from './edge-swipe-back.directive';

@Component({
  standalone: true,
  imports: [EdgeSwipeBackDirective],
  template: `<div class="shell" [asEdgeSwipeBack]="enabled()" [swipeTarget]="panes" style="width: 390px; height: 600px">
    <div #panes class="panes" style="height: 600px"></div>
  </div>`,
})
class HostComponent {
  readonly enabled = signal(true);
}

describe('EdgeSwipeBackDirective', () => {
  let panes: HTMLElement;
  let canSwipe: boolean;
  let swiped: jasmine.Spy;

  beforeEach(() => {
    canSwipe = true;
    swiped = jasmine.createSpy('swipeBack');
    TestBed.configureTestingModule({
      imports: [HostComponent],
      providers: [{ provide: NativeBackService, useValue: { canSwipeBack: () => canSwipe, swipeBack: swiped } }],
    });
    const fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
    panes = fixture.nativeElement.querySelector('.panes');
    document.body.appendChild(fixture.nativeElement);
  });

  function touch(type: string, x: number, y = 300): TouchEvent {
    const point = new Touch({ identifier: 1, target: panes, clientX: x, clientY: y });
    const event = new TouchEvent(type, {
      bubbles: true,
      cancelable: true,
      touches: type === 'touchend' ? [] : [point],
      changedTouches: [point],
    });
    panes.dispatchEvent(event);
    return event;
  }

  async function swipe(from: number, path: number[], y: number[] = path.map(() => 300)): Promise<void> {
    touch('touchstart', from);
    path.forEach((x, i) => touch('touchmove', x, y[i]));
    touch('touchend', path[path.length - 1]);
    await new Promise((resolve) => setTimeout(resolve, 300));
  }

  it('goes back when dragged from the left edge past a third of the screen', async () => {
    await swipe(8, [30, 120, 220]);
    expect(swiped).toHaveBeenCalledTimes(1);
  });

  it('moves the screen with the finger', () => {
    touch('touchstart', 8);
    const move = touch('touchmove', 108);
    expect(move.defaultPrevented).toBeTrue();
    expect(panes.style.transform).toContain('100px');
  });

  it('settles back without navigating when released early', async () => {
    touch('touchstart', 8);
    touch('touchmove', 40);
    await new Promise((resolve) => setTimeout(resolve, 40));
    touch('touchmove', 50);
    touch('touchend', 50);
    await new Promise((resolve) => setTimeout(resolve, 300));
    expect(swiped).not.toHaveBeenCalled();
    expect(panes.style.transform).toBe('');
  });

  it('leaves a touch away from the edge, or a vertical scroll, alone', async () => {
    await swipe(80, [200, 300]);
    await swipe(8, [12, 14, 16], [340, 400, 500]);
    expect(swiped).not.toHaveBeenCalled();
  });

  it('does nothing where back goes nowhere', async () => {
    canSwipe = false;
    await swipe(8, [120, 260]);
    expect(swiped).not.toHaveBeenCalled();
    expect(panes.style.transform).toBe('');
  });
});
