import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { DashaPayload } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { GuidedLifeChaptersComponent } from './guided-life-chapters.component';

function period(lord: string, start: string, end: string, active = false) {
  return { lord, start, end, years: 1, active };
}

const venusDashas = {
  system: 'vimshottari',
  cycle_years: 120,
  as_of: '2026-10-15',
  birth_nakshatra: { name: 'Bharani', lord: 'Venus', pada: 1, elapsed_fraction: 0.2, balance_years: 16 },
  mahadashas: [
    period('Venus', '2010-03-01', '2030-03-01', true),
    period('Sun', '2030-03-01', '2036-03-01'),
    period('Moon', '2036-03-01', '2046-03-01'),
  ],
  current: {
    mahadasha: period('Venus', '2010-03-01', '2030-03-01', true),
    pratyantardashas: [],
  },
} as unknown as DashaPayload;

describe('GuidedLifeChaptersComponent', () => {
  let fixture: ComponentFixture<GuidedLifeChaptersComponent>;
  let activeId: ReturnType<typeof signal<string | null>>;
  let dashas: jasmine.Spy<() => Promise<DashaPayload>>;

  beforeEach(async () => {
    activeId = signal<string | null>('profile-1');
    dashas = jasmine.createSpy('dashas').and.resolveTo(venusDashas);
    await TestBed.configureTestingModule({
      imports: [GuidedLifeChaptersComponent],
      providers: [
        provideRouter([]),
        { provide: KundliStore, useValue: { activeId, load: () => Promise.resolve() } },
        { provide: VedicService, useValue: { dashas } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(GuidedLifeChaptersComponent);
  });

  async function settle(): Promise<void> {
    fixture.detectChanges();
    await fixture.whenStable();
    await Promise.resolve();
    fixture.detectChanges();
  }

  it("renders the engine's running mahadasha, not an invented Saturn chapter", async () => {
    await settle();
    const text = fixture.nativeElement.textContent as string;
    expect(fixture.nativeElement.querySelector('.chapter-hero h2').textContent).toContain("Venus's Creative Phase");
    expect(text).toContain('2010');
    expect(text).toContain('2030');
    expect(text).not.toContain('Saturn');
    expect(text).not.toContain('2028');
    // The timeline shows up to four past chapters, the active one and the next one.
    const rows = fixture.nativeElement.querySelectorAll('.timeline article');
    expect(rows.length).toBe(2);
    expect(rows[0].classList).toContain('is-active');
    expect(rows[1].classList).toContain('is-future');
    expect(rows[1].textContent).toContain('Sun Chapter');
    expect(fixture.nativeElement.querySelectorAll('.insights article').length).toBe(3);
    expect(fixture.nativeElement.querySelector('.insights').textContent).toContain('Taste and agreement');
  });

  it('asks for birth details when there is no active profile', async () => {
    activeId.set(null);
    await settle();
    expect(dashas).not.toHaveBeenCalled();
    expect(fixture.nativeElement.querySelector('.chapter-hero')).toBeNull();
    expect(fixture.nativeElement.querySelectorAll('.timeline article').length).toBe(0);
    const link = fixture.nativeElement.querySelector('.life-state a');
    expect(link.textContent).toContain('Add birth details');
    expect(link.getAttribute('href')).toBe('/m/birth-details');
  });

  it('shows an empty state instead of a fabricated timeline when no dasha is running', async () => {
    dashas.and.resolveTo({ ...venusDashas, mahadashas: [], current: { pratyantardashas: [] } } as unknown as DashaPayload);
    await settle();
    expect(fixture.nativeElement.querySelector('.chapter-hero')).toBeNull();
    expect(fixture.nativeElement.querySelectorAll('.timeline article').length).toBe(0);
    expect(fixture.nativeElement.textContent).toContain('No running chapter');
    expect(fixture.nativeElement.textContent).not.toContain('Venus Chapter');
  });
});
