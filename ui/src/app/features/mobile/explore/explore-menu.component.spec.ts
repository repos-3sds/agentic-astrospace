import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { PlanGateService } from '../../../core/plan-gate.service';
import { PreferencesService } from '../../../core/preferences.service';
import { ExploreMenuComponent } from './explore-menu.component';

describe('ExploreMenuComponent', () => {
  const live = signal(false);
  const open = new Set<string>();

  function render(): HTMLElement {
    TestBed.configureTestingModule({
      imports: [ExploreMenuComponent],
      providers: [
        provideRouter([]),
        { provide: KundliStore, useValue: { active: signal({ name: 'Asha' }) } },
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
  });

  it('lists the eight entries in order, with Settings behind the gear', () => {
    const el = render();
    const labels = [...el.querySelectorAll('.explore-title')].map((node) => node.textContent?.trim());
    expect(labels).toEqual(['Birth details', 'Your chart', 'Yogas & doshas', 'Compatibility', 'Readings', 'Remedies', 'Muhurtas', 'Notes']);
    expect(el.querySelector('a[aria-label="Settings"]')?.getAttribute('href')).toBe('/m/settings');
    expect(el.querySelector('.plus')).toBeNull();
  });

  it('marks what Free leaves out once plans are enforced', () => {
    live.set(true);
    const el = render();
    const marks = [...el.querySelectorAll('.explore-card')].map((row) => [
      row.querySelector('.explore-title')?.textContent?.trim(),
      row.querySelector('.plus')?.textContent?.trim() ?? '',
    ]);
    expect(marks).toEqual([
      ['Birth details', ''], ['Your chart', ''], ['Yogas & doshas', 'Free · Plus'], ['Compatibility', 'Free · Plus'],
      ['Readings', 'Plus'], ['Remedies', 'Free · Plus'], ['Muhurtas', 'Plus'], ['Notes', ''],
    ]);
  });
});
