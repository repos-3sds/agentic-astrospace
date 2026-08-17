import { HttpErrorResponse } from '@angular/common/http';

import { ConnectivityService, isReachabilityFailure } from './connectivity.service';

describe('ConnectivityService', () => {
  let service: ConnectivityService;

  beforeEach(() => {
    service = new ConnectivityService();
  });

  it('distinguishes an unreachable device from a reachable API error', () => {
    expect(isReachabilityFailure(new HttpErrorResponse({ status: 0 }))).toBeTrue();
    expect(isReachabilityFailure(new TypeError('Failed to fetch'))).toBeTrue();
    expect(isReachabilityFailure(new HttpErrorResponse({ status: 500 }))).toBeFalse();
  });

  it('moves offline after a reachability failure but not an HTTP response', () => {
    service.noteRequestFailure(new TypeError('Failed to fetch'));
    expect(service.state()).toBe('offline');

    service.noteRequestFailure(new HttpErrorResponse({ status: 503 }));
    expect(service.state()).toBe('online');
  });

  it('verifies reachability before returning online', async () => {
    const fetchSpy = spyOn(window, 'fetch').and.resolveTo(new Response('{}', { status: 200 }));
    service.noteRequestFailure(new TypeError('Failed to fetch'));

    const retry = service.retry();
    expect(service.state()).toBe('reconnecting');
    expect(await retry).toBeTrue();
    expect(service.state()).toBe('online');
    expect(fetchSpy).toHaveBeenCalled();
  });

  it('returns to offline when the reachability probe fails', async () => {
    spyOn(window, 'fetch').and.rejectWith(new TypeError('Failed to fetch'));

    expect(await service.retry()).toBeFalse();
    expect(service.state()).toBe('offline');
  });
});
