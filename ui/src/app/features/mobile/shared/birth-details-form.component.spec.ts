import { fakeAsync, TestBed, tick } from '@angular/core/testing';

import { KundliPayload, PanchangaCity } from '../../../core/models';
import { PanchangaService } from '../../../core/panchanga.service';
import { BirthDetailsFormComponent } from './birth-details-form.component';

describe('BirthDetailsFormComponent', () => {
  const pune: PanchangaCity = {
    city: 'Pune', nation: 'IN', timezone: 'Asia/Kolkata', lat: 18.52, lng: 73.86, label: 'Pune, Maharashtra, India',
  };
  let cities: jasmine.Spy;

  beforeEach(async () => {
    cities = jasmine.createSpy('cities').and.resolveTo([pune]);
    await TestBed.configureTestingModule({
      imports: [BirthDetailsFormComponent],
      providers: [{ provide: PanchangaService, useValue: { cities } }],
    }).compileComponents();
  });

  function create() {
    const fixture = TestBed.createComponent(BirthDetailsFormComponent);
    fixture.detectChanges();
    return { fixture, form: fixture.componentInstance };
  }

  it('reports every missing field at once rather than only the last', () => {
    const { form } = create();
    expect(form.validate()).toBeNull();
    expect(Object.keys(form.fieldErrors()).sort()).toEqual(['date', 'name', 'place', 'time']);
  });

  it('refuses a typed place that was never chosen from the search', fakeAsync(() => {
    const { form } = create();
    form.name.set('Mira');
    form.date.set('2018-05-11');
    form.time.set('06:45');
    (form as unknown as { onPlaceInput(v: string): void }).onPlaceInput('Mumbaii');
    tick(250);
    tick();
    expect(form.validate()).toBeNull();
    expect(form.fieldErrors().place).toContain('search results');
  }));

  it('debounces the search and emits the chosen place, nation and accuracy', fakeAsync(() => {
    const { form } = create();
    const emitted: KundliPayload[] = [];
    form.submitted.subscribe((payload) => emitted.push(payload));
    form.name.set('Mira');
    form.relation.set('child');
    form.date.set('2018-05-11');
    const internals = form as unknown as {
      onPlaceInput(v: string): void; choosePlace(p: PanchangaCity): void; useApproximate(): void; onSubmit(e: Event): void;
    };
    internals.useApproximate();
    internals.onPlaceInput('P');
    internals.onPlaceInput('Pun');
    tick(249);
    expect(cities).not.toHaveBeenCalled();
    tick(1);
    expect(cities).toHaveBeenCalledOnceWith('Pun');
    tick();
    internals.choosePlace(pune);
    internals.onSubmit(new Event('submit'));

    expect(emitted).toEqual([jasmine.objectContaining({
      name: 'Mira', relation: 'child', birth_year: 2018, birth_month: 5, birth_day: 11,
      birth_hour: 6, birth_minute: 0, birth_city: 'Pune', birth_nation: 'IN', birth_time_accuracy: 'approximate',
    })]);
  }));

  it('trusts a saved place until it is edited, and keeps a locked relationship', () => {
    const { fixture, form } = create();
    fixture.componentRef.setInput('lockRelation', 'self');
    fixture.componentRef.setInput('initial', {
      name: 'Anika', relation: 'friend', birth_year: 1991, birth_month: 8, birth_day: 14,
      birth_hour: 6, birth_minute: 12, birth_city: 'Vijayawada', birth_nation: 'IN', birth_time_accuracy: 'exact',
    });
    expect(form.validate()).toEqual(jasmine.objectContaining({ relation: 'self', birth_city: 'Vijayawada', birth_minute: 12 }));
    (form as unknown as { onPlaceInput(v: string): void }).onPlaceInput('Vijayawad');
    expect(form.validate()).toBeNull();
  });

  it('does not offer "Myself" when the account already has one', () => {
    const { fixture, form } = create();
    fixture.componentRef.setInput('hideSelf', true);
    expect(form.relationOptions().some((o) => o.value === 'self')).toBeFalse();
  });

  it('clears only the message of the field being corrected', () => {
    const { form } = create();
    form.validate();
    (form as unknown as { onFieldInput(f: string, v: string): void }).onFieldInput('date', '1991-08-14');
    expect(form.fieldErrors().date).toBeUndefined();
    expect(form.fieldErrors().time).toBeDefined();
  });

  it('refuses a birth date in the future', () => {
    const { form } = create();
    form.date.set('2999-01-01');
    form.validate();
    expect(form.fieldErrors().date).toContain('future');
  });
});
