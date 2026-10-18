import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { FestivalService } from '../../../core/festival.service';
import { KundliStore } from '../../../core/kundli.store';
import { PanchangaService } from '../../../core/panchanga.service';
import { PreferencesService } from '../../../core/preferences.service';
import { CalendarComponent } from './calendar.component';

describe('CalendarComponent', () => {
  let fixture: ComponentFixture<CalendarComponent>;
  let resolveFestivals: ((value: { count: number; festivals: never[] }) => void) | undefined;

  beforeEach(async () => {
    const activeId = signal<string | null>('profile-1');
    const active = signal({
      id: 'profile-1',
      name: 'Test profile',
      birth_city: 'Singapore',
      birth_nation: 'SG',
    });
    const panchangaContextKey = signal('Singapore|SG|Asia/Singapore');
    const festivalRegions = signal<[]>([]);
    const panchangaPlace = signal({ city: 'Singapore', nation: 'SG', timezone: 'Asia/Singapore' });
    const pendingFestivals = new Promise<{ count: number; festivals: never[] }>((resolve) => {
      resolveFestivals = resolve;
    });

    await TestBed.configureTestingModule({
      imports: [CalendarComponent],
      providers: [
        provideRouter([]),
        { provide: KundliStore, useValue: { activeId, active } },
        {
          provide: PreferencesService,
          useValue: { panchangaContextKey, festivalRegions, panchangaPlace },
        },
        {
          provide: FestivalService,
          useValue: {
            cachedUpcoming: () => null,
            upcoming: () => pendingFestivals,
            refreshUpcoming: () => pendingFestivals,
            vratDays: (_place: unknown, fromDate: string) => Promise.resolve({
              days: [
                { date: fromDate.slice(0, 8) + '11', kind: 'ekadashi', paksha: 'Shukla', name: 'Shukla Ekadashi',
                  is_convention_dependent: true, observance_note: 'Smarta rule.' },
                { date: fromDate.slice(0, 8) + '15', kind: 'purnima', paksha: 'Shukla', name: 'Purnima',
                  is_convention_dependent: true, observance_note: 'Sunrise rule.' },
              ],
            }),
          },
        },
        {
          provide: PanchangaService,
          useValue: {
            month: (_id: string, fromDate: string) => Promise.resolve({
              note: 'Tarabala with Chandrabala at sunrise.',
              days: [
                { date: fromDate.slice(0, 8) + '03', quality: 'good', tara: 'Sampat', chandrabala_house: 1, chandrashtama: false },
                { date: fromDate.slice(0, 8) + '04', quality: 'care', tara: 'Vipat', chandrabala_house: 8, chandrashtama: true },
              ],
            }),
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CalendarComponent);
  });

  afterEach(() => resolveFestivals?.({ count: 0, festivals: [] }));

  it('renders the entire month before festival data resolves', () => {
    fixture.detectChanges();

    const dates = fixture.nativeElement.querySelectorAll('.mcal-grid a');
    expect(dates.length).toBeGreaterThanOrEqual(28);
    expect(dates.length).toBeLessThanOrEqual(31);
    expect(fixture.nativeElement.querySelector('[aria-label="Loading festivals"]')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('[aria-label="Loading calendar"]')).toBeNull();
  });

  it('tints days by quality, lists vrat days with their rule, and explains the marks (U7)', async () => {
    fixture.detectChanges();
    resolveFestivals?.({ count: 0, festivals: [] });
    await fixture.whenStable();
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;

    expect(el.querySelector('.mcal-q-good')).not.toBeNull();
    expect(el.querySelector('.mcal-q-care')?.getAttribute('aria-label')).toContain('a day to take care');
    const vrats = Array.from(el.querySelectorAll('.mcal-observance.vrat')).map((row) => row.textContent ?? '');
    expect(vrats.length).toBe(2);
    expect(vrats[0]).toContain('Shukla Ekadashi');
    expect(vrats[0]).toContain('Varies by tradition');
    expect(el.querySelector('.mcal-about:last-of-type')?.textContent).toContain('Smarta rule.');
    expect(el.querySelector('.mcal-legend')?.textContent).toContain('Take care');
    expect(el.querySelector('.mcal-about')?.textContent).toContain('Tarabala');
  });

  it('can go back a year', () => {
    fixture.detectChanges();
    const previous: HTMLButtonElement = fixture.nativeElement.querySelector('[aria-label="Previous month"]');
    expect(previous.disabled).toBeFalse();
  });
});
