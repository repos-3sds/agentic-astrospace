import { Component, viewChild } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Location } from '@angular/common';
import { provideLocationMocks } from '@angular/common/testing';
import { Router, provideRouter } from '@angular/router';
import { ScrollMemoryDirective } from './scroll-memory.directive';

@Component({ standalone: true, template: '' })
class BlankComponent {}

@Component({
  standalone: true,
  imports: [ScrollMemoryDirective],
  template: `<div asScrollMemory style="height: 200px; overflow-y: auto"><div style="height: 3000px"></div></div>`,
})
class HostComponent {
  readonly memory = viewChild.required(ScrollMemoryDirective);
}

describe('ScrollMemoryDirective', () => {
  let router: Router;
  let location: Location;
  let scroller: HTMLElement;
  let host: HostComponent;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      imports: [HostComponent],
      providers: [
        provideRouter([
          { path: '', pathMatch: 'full', redirectTo: 'm/today' },
          { path: 'm/today', component: BlankComponent },
          { path: 'm/explore', component: BlankComponent },
          { path: 'm/readings', component: BlankComponent },
        ]),
        provideLocationMocks(),
      ],
    });
    const fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
    host = fixture.componentInstance;
    scroller = fixture.nativeElement.querySelector('[asScrollMemory]');
    router = TestBed.inject(Router);
    location = TestBed.inject(Location);
    // Starts the location listener, so a back emits a popstate navigation.
    router.initialNavigation();
    await router.navigateByUrl('/m/today');
  });

  async function settle(): Promise<void> {
    await new Promise((resolve) => setTimeout(resolve, 120));
  }

  it('opens a forward destination at the top, not at the previous offset', async () => {
    scroller.scrollTop = 1200;
    await router.navigateByUrl('/m/explore');
    expect(scroller.scrollTop).toBe(0);
  });

  it('restores the offset on back', async () => {
    await router.navigateByUrl('/m/explore');
    scroller.scrollTop = 900;
    await router.navigateByUrl('/m/readings');
    expect(scroller.scrollTop).toBe(0);
    location.back();
    await settle();
    expect(location.path()).toBe('/m/explore');
    expect(scroller.scrollTop).toBe(900);
  });

  it('restores a retained tab root when it is reached again by a forward tap', async () => {
    scroller.scrollTop = 640;
    await router.navigateByUrl('/m/explore');
    expect(scroller.scrollTop).toBe(0);
    await router.navigateByUrl('/m/today');
    await settle();
    expect(scroller.scrollTop).toBe(640);
  });

  it('holds a restored offset when the outgoing screen leaves a frame later', async () => {
    scroller.scrollTop = 700;
    await router.navigateByUrl('/m/explore');
    await router.navigateByUrl('/m/today');
    // What the old screen's late removal does through scroll anchoring.
    requestAnimationFrame(() => { scroller.scrollTop = 18; });
    await settle();
    expect(scroller.scrollTop).toBe(700);
  });

  it('starts a non-tab screen at the top on a fresh forward visit', async () => {
    await router.navigateByUrl('/m/readings');
    scroller.scrollTop = 500;
    await router.navigateByUrl('/m/today');
    await router.navigateByUrl('/m/readings');
    expect(scroller.scrollTop).toBe(0);
  });

  it('restores a detail screen a tab press returns to', async () => {
    await router.navigateByUrl('/m/readings');
    scroller.scrollTop = 820;
    await router.navigateByUrl('/m/today');
    await router.navigateByUrl('/m/readings', { replaceUrl: true, state: { viaTab: true, restoreScroll: true } });
    await settle();
    expect(scroller.scrollTop).toBe(820);
  });

  it('leaves the offset alone when only the query string changes', async () => {
    scroller.scrollTop = 450;
    await router.navigateByUrl('/m/today?date=2026-10-16');
    expect(scroller.scrollTop).toBe(450);
  });

  it('scrolls to the top on request', async () => {
    scroller.scrollTop = 700;
    host.memory().scrollToTop();
    await new Promise((resolve) => setTimeout(resolve, 800));
    expect(scroller.scrollTop).toBe(0);
  });
});
