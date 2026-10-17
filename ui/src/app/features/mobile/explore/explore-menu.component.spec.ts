import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { PlanGateService } from '../../../core/plan-gate.service';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { ExploreMenuComponent } from './explore-menu.component';

describe('ExploreMenuComponent', () => {
  const live = signal(false);
  const open = new Set<string>();
  const owner = signal<{ id: string; name: string } | null>(null);

  function render(): HTMLElement {
    TestBed.configureTestingModule({
      imports: [ExploreMenuComponent],
      providers: [
        provideRouter([]),
        { provide: KundliStore, useValue: { active: signal({ id: 'k-asha', name: 'Asha Rao', birth_city: 'Pune', birth_hour: 6, birth_minute: 5 }), activeId: signal(null), owner } },
        { provide: VedicService, useValue: {} },
        { provide: PreferencesService, useValue: { experienceMode: signal('balanced') } },
        { provide: PlanGateService, useValue: { live, allows: (key: string) => !live() || open.has(key) } },
      ],
    });
    const fixture = TestBed.createComponent(ExploreMenuComponent);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  beforeEach(() => {
    live.set(false);
    open.clear();
    owner.set(null);
  });

  it('greets the person and lists the eight tiles in order, with Settings behind the gear', () => {
    const el = render();
    const labels = [...el.querySelectorAll('.tile-title')].map((node) => node.textContent?.trim());
    expect(labels).toEqual(['Birth details', 'Yogas & doshas', 'Life periods', 'Compatibility', 'Readings', 'Remedies', 'Muhurtas', 'Notes']);
    expect(el.querySelector('.who-text b')?.textContent?.trim()).toBe('Namaste, Asha');
    expect(el.querySelector('.featured')?.getAttribute('href')).toBe('/m/chart');
    expect(el.querySelector('a[aria-label="Settings"]')?.getAttribute('href')).toBe('/m/settings');
    expect(el.querySelector('.plus')).toBeNull();
  });

  it('marks what Free leaves out once plans are enforced', () => {
    live.set(true);
    const el = render();
    const marks = [...el.querySelectorAll('.tile')].map((row) => [
      row.querySelector('.tile-title')?.textContent?.trim(),
      row.querySelector('.plus')?.textContent?.trim() ?? '',
    ]);
    expect(marks).toEqual([
      ['Birth details', ''], ['Yogas & doshas', 'Free · Plus'], ['Life periods', ''], ['Compatibility', 'Free · Plus'],
      ['Readings', 'Plus'], ['Remedies', 'Free · Plus'], ['Muhurtas', 'Plus'], ['Notes', ''],
    ]);
  });

  it('greets the account holder while showing whose chart is open', () => {
    owner.set({ id: 'k-me', name: 'Hawk Varma' });
    const el = render();
    expect(el.querySelector('.who-text b')?.textContent?.trim()).toBe('Namaste, Hawk');
    expect(el.querySelector('.who-text em')?.textContent?.trim()).toBe('Viewing Asha · tap to switch');
  });
});
