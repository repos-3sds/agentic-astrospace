import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { ApiService } from './api.service';
import { AuthService } from './auth.service';
import { PushService } from './push.service';

describe('PushService', () => {
  it('registers again when someone signs in after boot, without a restart', async () => {
    const session = signal<{ user: { id: string } } | null>({ user: { id: 'u1' } });
    TestBed.configureTestingModule({
      providers: [
        { provide: ApiService, useValue: {} },
        { provide: AuthService, useValue: { session, isAuthenticated: () => !!session() } },
      ],
    });
    const push = TestBed.inject(PushService);
    TestBed.tick();
    await push.init(); // boot
    const init = spyOn(push, 'init').and.resolveTo();

    session.set(null); // signed out
    TestBed.tick();
    expect(init).not.toHaveBeenCalled();

    session.set({ user: { id: 'u1' } }); // signed back in, same app session
    TestBed.tick();
    expect(init).toHaveBeenCalledTimes(1);
  });
});
