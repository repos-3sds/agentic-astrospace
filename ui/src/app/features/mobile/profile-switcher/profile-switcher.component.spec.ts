import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { KundliStore } from '../../../core/kundli.store';
import { Kundli } from '../../../core/models';
import { ProfileSwitcherComponent } from './profile-switcher.component';

describe('ProfileSwitcherComponent', () => {
  it('changes the active profile through the store exactly once', () => {
    const setActive = jasmine.createSpy('setActive');
    TestBed.configureTestingModule({
      providers: [{
        provide: KundliStore,
        useValue: {
          activeId: signal<string | null>('profile-a'),
          kundlis: signal<Kundli[]>([]),
          setActive,
        },
      }],
    });
    const component = TestBed.runInInjectionContext(() => new ProfileSwitcherComponent());
    const dismissed = jasmine.createSpy('dismissed');
    component.dismissed.subscribe(dismissed);

    (component as unknown as { choose(profile: Kundli): void }).choose({ id: 'profile-b' } as Kundli);

    expect(setActive).toHaveBeenCalledOnceWith('profile-b');
    expect(dismissed).toHaveBeenCalledTimes(1);
    expect('selected' in component).toBeFalse();
  });
});
