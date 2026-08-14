import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { ConfirmationService, MessageService } from 'primeng/api';

import { AdminService } from '../../core/admin.service';
import { AuthService } from '../../core/auth.service';
import { KundliStore } from '../../core/kundli.store';
import { ThemeService } from '../../core/theme.service';
import { SidebarComponent } from './sidebar.component';

describe('SidebarComponent admin access check', () => {
  it('checks admin access once per authenticated user identity', async () => {
    const ready = signal(true);
    const user = signal<{ id: string } | null>({ id: 'user-a' });
    const admin = jasmine.createSpyObj<AdminService>('AdminService', ['me']);
    admin.me.and.resolveTo({} as never);

    TestBed.configureTestingModule({
      providers: [
        {
          provide: AuthService,
          useValue: {
            ready,
            user,
            init: () => Promise.resolve(),
          },
        },
        { provide: AdminService, useValue: admin },
        {
          provide: KundliStore,
          useValue: {
            kundlis: signal([]),
            activeId: signal(null),
          },
        },
        { provide: ThemeService, useValue: { dark: signal(false), toggle: () => undefined } },
        { provide: ConfirmationService, useValue: { confirm: () => undefined } },
        { provide: MessageService, useValue: { add: () => undefined } },
        { provide: Router, useValue: jasmine.createSpyObj<Router>('Router', ['navigate']) },
      ],
    });

    TestBed.runInInjectionContext(() => new SidebarComponent());
    TestBed.flushEffects();
    await Promise.resolve();
    expect(admin.me).toHaveBeenCalledTimes(1);

    // Supabase getSession() commonly emits a new User object for the same ID
    // while preparing an authenticated request. That must not start another
    // admin check.
    user.set({ id: 'user-a' });
    TestBed.flushEffects();
    await Promise.resolve();
    expect(admin.me).toHaveBeenCalledTimes(1);

    user.set({ id: 'user-b' });
    TestBed.flushEffects();
    await Promise.resolve();
    expect(admin.me).toHaveBeenCalledTimes(2);
  });
});
