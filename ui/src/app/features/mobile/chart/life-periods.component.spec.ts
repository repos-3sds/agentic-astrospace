import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { provideRouter } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { DashaPayload } from '../../../core/models';
import { PlanGateService } from '../../../core/plan-gate.service';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { LifePeriodsComponent } from './life-periods.component';

function payload(lord: string, extra: Record<string, unknown> = {}): DashaPayload {
  const maha = { lord, start: '2020-01-01T00:00:00', end: '2040-01-01T00:00:00', years: 20, active: true, antardashas: [] };
  return {
    system: 'Vimshottari', cycle_years: 120,
    birth_nakshatra: { name: 'Ashwini', lord: 'Ketu', pada: 1, elapsed_fraction: 0, balance_years: 7 },
    as_of: '2026-10-24T00:00:00', mahadashas: [maha], current: { mahadasha: maha, pratyantardashas: [] },
    ...extra,
  } as DashaPayload;
}

describe('LifePeriodsComponent Vimshottari starts', () => {
  let allows: (key: string) => boolean;
  let variant: jasmine.Spy;
  let mode: string;

  async function setup(): Promise<ComponentFixture<LifePeriodsComponent>> {
    variant = jasmine.createSpy('dashaVariant').and.resolveTo(
      payload('Moon', { system: 'Vimshottari from Kshema Tara', variant: 'kshema', observance_note: 'One of several starting points.' }),
    );
    TestBed.configureTestingModule({
      imports: [LifePeriodsComponent],
      providers: [
        provideRouter([]),
        { provide: KundliStore, useValue: { activeId: signal('k1'), active: signal(null), load: () => Promise.resolve() } },
        {
          provide: VedicService,
          useValue: {
            cachedAll: () => null,
            dashas: () => Promise.resolve(payload('Saturn')),
            yoginiDashas: () => Promise.resolve(null),
            dashaVariant: variant,
          },
        },
        { provide: PreferencesService, useValue: { experienceMode: signal(mode) } },
        { provide: PlanGateService, useValue: { allows: (key: string) => allows(key), live: signal(true) } },
      ],
    });
    const fixture = TestBed.createComponent(LifePeriodsComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    return fixture;
  }

  it('offers the Start from list to a Practitioner plan and shows the chosen variant', async () => {
    allows = () => true;
    mode = 'balanced';
    const fixture = await setup();
    const select = fixture.nativeElement.querySelector('.start-from select') as HTMLSelectElement;
    expect(select).toBeTruthy();
    expect(select.options.length).toBe(8);
    expect(fixture.nativeElement.querySelector('.active-period h2').textContent).toContain('Saturn');

    select.value = 'kshema';
    select.dispatchEvent(new Event('change'));
    await fixture.whenStable();
    fixture.detectChanges();
    expect(variant).toHaveBeenCalledWith('k1', 'kshema');
    expect(fixture.nativeElement.querySelector('.active-period h2').textContent).toContain('Moon');
    expect(fixture.nativeElement.textContent).toContain('One of several starting points.');
  });

  it('hides the Start from list without the Practitioner plan', async () => {
    allows = (key) => key !== 'dashas.variants';
    mode = 'balanced';
    const fixture = await setup();
    expect(fixture.nativeElement.querySelector('.active-period h2').textContent).toContain('Saturn');
    expect(fixture.nativeElement.querySelector('.start-from')).toBeNull();
  });

  it('gives Practitioner one dense screen: the running chain and an inline tree', async () => {
    allows = () => true;
    mode = 'practitioner';
    const fixture = await setup();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.active-period')).toBeNull();
    expect(el.querySelector('.levels')).toBeNull();
    expect(el.querySelector('.chain-row b')?.textContent).toBe('Saturn');
    const nodes = () => Array.from(el.querySelectorAll('.tree .node'));
    expect(nodes().length).toBe(1);
    expect(el.querySelector('.start-select')).toBeTruthy();
  });
});
