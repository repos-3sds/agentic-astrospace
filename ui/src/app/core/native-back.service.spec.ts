import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideLocationMocks } from '@angular/common/testing';
import { Router, provideRouter } from '@angular/router';

import { NativeBackService } from './native-back.service';
import { NavigationHistoryService, TabNavigationState } from './navigation-history.service';
import { activeTabRoots } from './tab-roots';

@Component({ standalone: true, template: '' })
class BlankComponent {}

const TAB: TabNavigationState = { viaTab: true, restoreScroll: true };

describe('NativeBackService', () => {
  let router: Router;
  let history: NavigationHistoryService;
  let back: NativeBackService;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter(
          ['m/start', 'm/onboarding', 'm/today', 'm/ask', 'm/ask/answer', 'm/explore', 'm/readings', 'm/calendar', 'm/calendar/day']
            .map((path) => ({ path, component: BlankComponent })),
        ),
        provideLocationMocks(),
      ],
    });
    router = TestBed.inject(Router);
    history = TestBed.inject(NavigationHistoryService);
    back = TestBed.inject(NativeBackService);
    activeTabRoots.set(['/m/today', '/m/ask', '/m/calendar', '/m/explore', '/m/settings']);
    // Starts the location listener, so history.go emits a popstate navigation.
    router.initialNavigation();
    await router.navigateByUrl('/m/start');
    await router.navigateByUrl('/m/onboarding');
    history.enterShell();
    await router.navigateByUrl('/m/today');
  });

  afterEach(() => activeTabRoots.set([]));

  async function until(url: string): Promise<void> {
    for (let i = 0; i < 50 && router.url !== url; i++) await new Promise((r) => setTimeout(r, 5));
    expect(router.url).toBe(url);
  }

  it('returns from Ask to the Today that opened it (Deepak, 2026-10-28)', async () => {
    await router.navigateByUrl('/m/ask?q=Why%20is%20today%20supportive');
    await router.navigate(['/m/ask'], { replaceUrl: true });
    // Sent from a handoff, the answer replaces Ask (AskHomeComponent).
    await router.navigate(['/m/ask/answer'], { queryParams: { thread: 't1' }, replaceUrl: true });
    expect(back.canSwipeBack()).toBeTrue();
    back.hardwareBack();
    await until('/m/today');
  });

  it('never walks back out of the tabs into onboarding', async () => {
    expect(back.canSwipeBack()).toBeFalse();
    await router.navigateByUrl('/m/explore', { replaceUrl: true, state: TAB });
    expect(back.canSwipeBack()).toBeFalse();
    back.hardwareBack();
    await until('/m/today');
  });

  it('takes a tab root opened from the tab bar to Today, not to the tab before it', async () => {
    await router.navigateByUrl('/m/explore', { replaceUrl: true, state: TAB });
    await router.navigateByUrl('/m/readings');
    await router.navigateByUrl('/m/calendar', { replaceUrl: true, state: TAB });
    back.hardwareBack();
    await until('/m/today');
  });

  it('skips a copy of the same screen, so one back always moves', async () => {
    await router.navigateByUrl('/m/calendar', { replaceUrl: true, state: TAB });
    await router.navigateByUrl('/m/calendar/day?date=2026-10-28');
    await router.navigateByUrl('/m/calendar/day?date=2026-10-29');
    back.hardwareBack();
    await until('/m/calendar');
  });

  it('steps back to a screen already in the history for a tab press', async () => {
    await router.navigateByUrl('/m/ask?q=x');
    expect(history.stepsBackTo('/m/today')).toBe(-1);
    history.go(-1);
    await until('/m/today');
    // The jump was counted: nothing in the tabs is behind Today now.
    expect(history.stepsBack()).toBeNull();
  });

  it('sends a screen opened straight from a notification to Today', async () => {
    await router.navigateByUrl('/m/calendar/day?date=2026-10-28', { replaceUrl: true });
    back.hardwareBack();
    await until('/m/today');
  });
});
