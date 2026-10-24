import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { of } from 'rxjs';

import { KundliStore } from '../../../core/kundli.store';
import { VedicAll } from '../../../core/models';
import { PlanGateService } from '../../../core/plan-gate.service';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { ChartFullComponent } from './chart-full.component';

// Sun in Cancer in D1, Pisces in D9: the table has to follow the chip.
const CHART = {
  planets: {
    Sun: { sign: 'Cancer', dms: '28°37\'10"', nakshatra: 'Ashlesha', nakshatra_pada: 4, house: 12, retrograde: false },
  },
  dignities: { Sun: { dignity: 'neutral' } },
  vargas: {
    D9: {
      name: 'Navamsha', signifies: '', verified_rule: true, lagna: { sign: 'Gemini' },
      planets: { Sun: { sign: 'Pisces', house: 10, retrograde: false, dignity: 'Neutral', dms: '17°34\'15"', nakshatra: 'Revati', nakshatra_pada: 1 } },
      degree_convention: { is_convention_dependent: true, observance_note: 'Varga longitude convention.' },
    },
    D10: {
      name: 'Dashamsha', signifies: '', verified_rule: true, lagna: { sign: 'Libra' },
      planets: { Sun: { sign: 'Sagittarius', house: 3, retrograde: false, dignity: 'Neutral' } },
    },
  },
} as unknown as VedicAll;

type Rows = {
  selectedVarga: { set(v: string): void };
  isRashi: () => boolean;
  planetRows: () => Array<{ planet: string; sign: string; house: number | string; degree: string; nakshatra: string; pada: number | string; dignity: string }>;
  degreeNote: () => string | null;
  chart: { set(v: VedicAll): void };
};

describe('ChartFullComponent planetary positions', () => {
  let component: Rows;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { queryParamMap: of(convertToParamMap({})) } },
        { provide: KundliStore, useValue: { activeId: signal(null), active: signal(null), load: () => Promise.resolve() } },
        { provide: VedicService, useValue: { cachedAll: () => null } },
        { provide: PlanGateService, useValue: { allows: () => true } },
        { provide: PreferencesService, useValue: { experienceMode: signal('practitioner'), chartStyle: signal('south') } },
      ],
    });
    component = TestBed.runInInjectionContext(() => new ChartFullComponent()) as unknown as Rows;
    component.chart.set(CHART);
  });

  it('shows D1 degree and nakshatra on D1', () => {
    component.selectedVarga.set('D1');
    expect(component.isRashi()).toBeTrue();
    expect(component.planetRows()[0]).toEqual(jasmine.objectContaining({ sign: 'Cancer', house: 12, degree: '28°37\'10"', nakshatra: 'Ashlesha' }));
    expect(component.degreeNote()).toBeNull();
  });

  it('shows each varga its own sign, house, degree, nakshatra and dignity', () => {
    component.selectedVarga.set('D9');
    expect(component.isRashi()).toBeFalse();
    expect(component.planetRows()[0]).toEqual(jasmine.objectContaining({
      planet: 'Sun', sign: 'Pisces', house: 10, degree: '17°34\'15"', nakshatra: 'Revati', pada: 1, dignity: 'Neutral',
    }));
    expect(component.degreeNote()).toContain('convention');

    component.selectedVarga.set('D10');
    expect(component.planetRows()[0].sign).toBe('Sagittarius');
    expect(component.planetRows()[0].house).toBe(3);
    expect(component.planetRows()[0].degree).toBe('—');
  });

  it('shows no rows rather than D1 values when a varga is missing', () => {
    component.selectedVarga.set('D60');
    expect(component.planetRows()).toEqual([]);
  });
});
