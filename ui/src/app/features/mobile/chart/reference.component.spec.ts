import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { AshtakavargaPayload } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { ReferenceComponent } from './reference.component';

const PLANETS = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn'];
const SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'];

function payload(): AshtakavargaPayload {
  // Deterministic bindus: planet p gives (p + sign) % 5 to each sign.
  const bav: Record<string, number[]> = {};
  PLANETS.forEach((planet, p) => { bav[planet] = SIGNS.map((_, s) => (p + s) % 5); });
  const sav = SIGNS.map((_, s) => PLANETS.reduce((sum, planet) => sum + bav[planet][s], 0));
  return {
    planets: PLANETS,
    sources: [...PLANETS, 'Lagna'],
    bav,
    sav,
    signs: SIGNS.map((sign, index) => ({
      index, sign, sav: sav[index],
      bav: Object.fromEntries(PLANETS.map((planet) => [planet, bav[planet][index]])),
    })),
    pinda_rank: [
      { planet: 'Jupiter', rashi_pinda: 100, graha_pinda: 40, shodhya_pinda: 140 },
      { planet: 'Sun', rashi_pinda: 60, graha_pinda: 20, shodhya_pinda: 80 },
    ],
    totals: {
      bav: Object.fromEntries(PLANETS.map((planet) => [planet, bav[planet].reduce((a, b) => a + b, 0)])),
      sav: sav.reduce((a, b) => a + b, 0),
    },
  } as AshtakavargaPayload;
}

describe('ReferenceComponent (ashtakavarga)', () => {
  let fixture: ComponentFixture<ReferenceComponent>;
  let ashtakavarga: jasmine.Spy<() => Promise<AshtakavargaPayload>>;

  beforeEach(async () => {
    ashtakavarga = jasmine.createSpy('ashtakavarga').and.resolveTo(payload());
    await TestBed.configureTestingModule({
      imports: [ReferenceComponent],
      providers: [
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { snapshot: { data: { referenceMode: 'ashtakavarga' } } } },
        {
          provide: KundliStore,
          useValue: { activeId: signal('profile-1'), active: signal({ id: 'profile-1' }), load: () => Promise.resolve() },
        },
        { provide: VedicService, useValue: { ashtakavarga } },
      ],
    }).compileComponents();
  });

  // The component fetches in its constructor, so create it after any stub override.
  async function settle(): Promise<void> {
    fixture = TestBed.createComponent(ReferenceComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    await Promise.resolve();
    fixture.detectChanges();
  }

  it('renders the 12-sign by 7-planet bindu matrix with SAV and totals', async () => {
    await settle();
    const el = fixture.nativeElement as HTMLElement;
    const body = el.querySelectorAll('table[aria-label="Bindus by sign and planet"] tbody tr');
    expect(body.length).toBe(12);
    const header = el.querySelectorAll('table[aria-label="Bindus by sign and planet"] thead th');
    expect(header.length).toBe(1 + 7 + 1);
    expect(header[1].textContent?.trim()).toBe('Su');
    expect(header[8].textContent?.trim()).toBe('SAV');

    // Aries row: Sun gives 0, Moon 1, ... Jupiter 4, Venus 0, Saturn 1 → SAV 11.
    const aries = body[0].querySelectorAll('th, td');
    expect(aries[0].textContent?.trim()).toBe('Ari');
    expect(Array.from(aries).slice(1, 8).map((cell) => cell.textContent?.trim())).toEqual(['0', '1', '2', '3', '4', '0', '1']);
    expect(aries[8].textContent?.trim()).toBe('11');

    const foot = el.querySelectorAll('table[aria-label="Bindus by sign and planet"] tfoot td');
    expect(foot[7].textContent?.trim()).toBe(String(payload().totals.sav));
    expect(el.querySelector('.av-summary')?.textContent).toContain('of 337');
  });

  it('ranks shodhya pinda and never shows the old flattened key dump', async () => {
    await settle();
    const el = fixture.nativeElement as HTMLElement;
    const pinda = el.querySelectorAll('table[aria-label="Shodhya pinda by planet"] tbody tr');
    expect(pinda.length).toBe(2);
    expect(pinda[0].textContent).toContain('Jupiter');
    expect(pinda[0].textContent).toContain('140');
    expect(el.textContent).not.toContain('planets · 0');
    expect(el.querySelector('.ref-row')).toBeNull();
  });

  it('shows an empty state when the payload has no signs', async () => {
    ashtakavarga.and.resolveTo({ ...payload(), signs: [] });
    await settle();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('table')).toBeNull();
    expect(el.textContent).toContain('No Ashtakavarga tables came back');
  });
});
