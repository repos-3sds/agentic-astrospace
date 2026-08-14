import { fakeAsync, TestBed, tick } from '@angular/core/testing';

import { PanchangaCity } from '../../../core/models';
import { PanchangaService } from '../../../core/panchanga.service';
import { BirthPlaceFieldComponent } from './birth-place-field.component';

describe('BirthPlaceFieldComponent', () => {
  const singapore: PanchangaCity = {
    city: 'Singapore', nation: 'SG', timezone: 'Asia/Singapore', lat: 1.3521, lng: 103.8198,
    label: 'Singapore, Singapore',
  };
  let cities: jasmine.Spy;

  beforeEach(async () => {
    cities = jasmine.createSpy('cities').and.resolveTo([singapore]);
    await TestBed.configureTestingModule({
      imports: [BirthPlaceFieldComponent],
      providers: [{ provide: PanchangaService, useValue: { cities } }],
    }).compileComponents();
  });

  it('debounces lookup and emits only a selected canonical place', fakeAsync(() => {
    const fixture = TestBed.createComponent(BirthPlaceFieldComponent);
    const component = fixture.componentInstance;
    const emitted: Array<PanchangaCity | null> = [];
    component.placeChange.subscribe((place) => emitted.push(place));

    component.search('S');
    component.search('Sing');
    tick(249);
    expect(cities).not.toHaveBeenCalled();
    tick(1);
    expect(cities).toHaveBeenCalledOnceWith('Sing');
    tick();

    component.choose(singapore);
    expect(component.query()).toBe('Singapore');
    expect(emitted.at(-1)).toEqual(singapore);
  }));

  it('invalidates a previous selection as soon as the user edits it', () => {
    const fixture = TestBed.createComponent(BirthPlaceFieldComponent);
    fixture.componentRef.setInput('initialPlace', { city: 'Singapore', nation: 'SG' });
    fixture.detectChanges();
    const emitted: Array<PanchangaCity | null> = [];
    fixture.componentInstance.placeChange.subscribe((place) => emitted.push(place));

    fixture.componentInstance.search('London');

    expect(fixture.componentInstance.selected()).toBeNull();
    expect(emitted).toEqual([null]);
  });
});
