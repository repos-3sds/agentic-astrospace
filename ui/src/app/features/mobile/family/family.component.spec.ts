import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';

import { EntitlementService } from '../../../core/entitlement.service';
import { KundliStore } from '../../../core/kundli.store';
import { FamilyComponent } from './family.component';

const person = (id: string, name: string, relation: string, moon_sign?: string) =>
  ({ id, name, relation, moon_sign, birth_city: 'Pune' }) as never;

describe('FamilyComponent', () => {
  const kundlis = signal([
    person('k3', 'Ravi', 'friend'),
    person('k2', 'Meera', 'child', 'Leo'),
    person('k1', 'Anika', 'self', 'Scorpio'),
  ]);
  const activeId = signal<string | null>('k1');
  let setActive: jasmine.Spy;

  beforeEach(async () => {
    activeId.set('k1');
    setActive = jasmine.createSpy('setActive').and.callFake((id: string) => activeId.set(id));
    await TestBed.configureTestingModule({
      imports: [FamilyComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        {
          provide: KundliStore,
          useValue: {
            kundlis, activeId, setActive,
            loaded: signal(true),
            load: async () => undefined,
            active: () => kundlis().find((k) => (k as { id: string }).id === activeId()),
          },
        },
        {
          provide: EntitlementService,
          useValue: {
            current: signal({ quotas_enforced: true, entitlements: { 'profiles.max': 3 } }),
            refresh: async () => undefined,
          },
        },
      ],
    }).compileComponents();
  });

  async function render(): Promise<HTMLElement> {
    const fixture = TestBed.createComponent(FamilyComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  it('lists yourself first, family before friends, and marks who is showing', async () => {
    const el = await render();
    const names = [...el.querySelectorAll('.who b')].map((b) => b.textContent);
    expect(names).toEqual(['Anika', 'Meera', 'Ravi']);
    expect([...el.querySelectorAll('.eyebrow')].map((e) => e.textContent)).toEqual(['FAMILY', 'FRIENDS & OTHERS']);
    expect(el.querySelector('.person.is-active .who b')?.textContent).toBe('Anika');
    expect(el.textContent).toContain('Myself · Scorpio Moon');
    expect(el.textContent).toContain('3 of 3 profiles on your plan.');
  });

  it('switches whose reading shows without leaving the list', async () => {
    const el = await render();
    const meera = [...el.querySelectorAll<HTMLButtonElement>('.person-main')].find((b) => b.textContent?.includes('Meera'))!;
    meera.click();
    expect(setActive).toHaveBeenCalledWith('k2');
  });
});
