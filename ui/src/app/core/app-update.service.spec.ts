import { TestBed } from '@angular/core/testing';
import { AppUpdateService, AppVersionStatus } from './app-update.service';
import { ApiService } from './api.service';

const status = (s: AppVersionStatus['status'], platform: 'android' | 'ios' = 'android'): AppVersionStatus => ({
  platform, build: 640, status: s, latest_build: 650, required_build: null,
  update_url: platform === 'ios' ? 'itms-beta://x' : 'https://play.google.com/store/apps/details?id=app.asksiddha.mobile',
});

describe('AppUpdateService', () => {
  let svc: AppUpdateService;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ providers: [{ provide: ApiService, useValue: {} }] });
    svc = TestBed.inject(AppUpdateService);
  });

  it('offers nothing while the build is current', () => {
    svc.status.set(status('current'));
    expect(svc.offer()).toBeFalse();
    expect(svc.blocked()).toBeFalse();
  });

  it('offers the update, and Later puts it away', () => {
    svc.status.set(status('update_available'));
    expect(svc.offer()).toBeTrue();
    svc.later();
    expect(svc.offer()).toBeFalse();
  });

  it('waits for Play on Android: no offer while Play says it has nothing yet', () => {
    svc.status.set(status('update_available'));
    (svc as unknown as { playHasIt: { set(v: boolean | null): void } }).playHasIt.set(false);
    expect(svc.offer()).toBeFalse();
  });

  it('blocks only when the server says the build is required, whatever Play says', () => {
    svc.status.set(status('update_required'));
    (svc as unknown as { playHasIt: { set(v: boolean | null): void } }).playHasIt.set(false);
    expect(svc.blocked()).toBeTrue();
  });

  it('names the store the phone updates from', () => {
    svc.status.set(status('update_available', 'ios'));
    expect(svc.store()).toBe('TestFlight');
    svc.status.set(status('update_available', 'android'));
    expect(svc.store()).toBe('Google Play');
  });

  it('opens the update link', async () => {
    const open = spyOn(window, 'open');
    svc.status.set(status('update_required', 'ios'));
    await svc.update();
    expect(open).toHaveBeenCalledWith('itms-beta://x', '_system');
  });
});
