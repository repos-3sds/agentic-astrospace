import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { FestivalService } from '../../../core/festival.service';
import { KundliStore } from '../../../core/kundli.store';
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
});
