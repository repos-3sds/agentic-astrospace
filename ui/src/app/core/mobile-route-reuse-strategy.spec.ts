import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, DetachedRouteHandle, Route, UrlSegment } from '@angular/router';

import { MobileRouteReuseStrategy } from './mobile-route-reuse-strategy';
import { SessionTeardown } from './session-teardown';

function snapshot(path: string, parent: ActivatedRouteSnapshot | null, config: Route = { path }): ActivatedRouteSnapshot {
  return {
    url: path ? path.split('/').map((p) => new UrlSegment(p, {})) : [],
    parent,
    routeConfig: config,
  } as unknown as ActivatedRouteSnapshot;
}

const created: Element[] = [];

function handle(connected: boolean): { handle: DetachedRouteHandle; destroy: jasmine.Spy } {
  const element = document.createElement('div');
  created.push(element);
  if (connected) document.body.appendChild(element);
  const destroy = jasmine.createSpy('destroy');
  return { handle: { componentRef: { location: { nativeElement: element }, destroy } } as DetachedRouteHandle, destroy };
}

describe('MobileRouteReuseStrategy sign-out', () => {
  let strategy: MobileRouteReuseStrategy;
  const root = snapshot('', null);
  const shellConfig: Route = { path: 'm' };
  const shell = snapshot('m', root, shellConfig);
  const today = snapshot('today', shell);
  const settings = snapshot('settings', shell);

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [MobileRouteReuseStrategy] });
    strategy = TestBed.inject(MobileRouteReuseStrategy);
  });

  afterEach(() => created.splice(0).forEach((el) => el.remove()));

  it('retains footer tabs while signed in', () => {
    const today1 = handle(false);
    expect(strategy.shouldDetach(today)).toBeTrue();
    strategy.store(today, today1.handle);
    expect(strategy.shouldAttach(today)).toBeTrue();
    expect(strategy.retrieve(today)).toBe(today1.handle);
  });

  it('destroys retained views on sign-out so the next account never sees them', () => {
    const parked = handle(false);
    const onScreen = handle(true);
    strategy.store(today, parked.handle);
    strategy.store(settings, onScreen.handle);

    TestBed.inject(SessionTeardown).run();

    expect(parked.destroy).toHaveBeenCalled();
    // The view on screen is left to the router, which destroys it on the way out.
    expect(onScreen.destroy).not.toHaveBeenCalled();
    expect(strategy.shouldAttach(today)).toBeFalse();
    expect(strategy.retrieve(settings)).toBeNull();
  });

  it('does not park the tab being left during the sign-out navigation', () => {
    TestBed.inject(SessionTeardown).run();

    expect(strategy.shouldDetach(settings)).toBeFalse();
  });

  it('retains tabs again once the native shell is re-entered after sign-in', () => {
    TestBed.inject(SessionTeardown).run();

    strategy.shouldAttach(shell);

    expect(strategy.shouldDetach(today)).toBeTrue();
  });
});
