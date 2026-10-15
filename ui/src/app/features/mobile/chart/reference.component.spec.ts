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

describe('ReferenceComponent (avkahada and favourable)', () => {
  const chart = {
    avkahada: {
      lagna: 'Aries', lagna_sanskrit: 'Mesha', lagna_lord: 'Mars', rashi: 'Libra', rashi_sanskrit: 'Tula', rashi_lord: 'Venus',
      nakshatra: 'Swati', nakshatra_lord: 'Rahu', charan: 2, tithi: 'Chaturthi Krishna', yoga: 'Vyaghata', karana: 'Bava',
      varna: 'Shudra', gana: 'Deva', nadi: 'Antya', first_letters: ['Ru', 'Re', 'Ro', 'Ta'], name_letter: 'Re', vara: 'Thursday',
    },
    ghatak: { rashi: 'Capricorn', rashi_sanskrit: 'Makara', month: 'Jyeshtha', tithi: '4, 9, 14', day: 'Thursday', nakshatra: 'Shatabhisha', lagna: 'Libra', lagna_sanskrit: 'Tula', yoga: null, karana: null, prahar: null },
    favourable: {
      lucky_number: 6, ruling_planet: 'Venus', good_numbers: [3, 6, 9], evil_numbers: [1, 8], good_years: [6, 15],
      lucky_days: ['Thursday'], good_planets: ['Jupiter'], evil_planets: ['Saturn'], yogakaraka: null, friendly_signs: ['Aries'],
      lucky_metal: 'Copper', lucky_stone: 'Red Coral', lucky_direction: 'South', lucky_time: 'Hora of Mars',
      lucky_color: { name: 'Coral Red', hex: '#D0342C', planet: 'Mars', source: 'colour of Mars, the Lagna lord' },
      astrological_number: { number: 9, planet: 'Mars', source: 'Lagna lord', witnesses: [], confirmed_by: ['Nakshatra lord'], confirmation_count: 1 },
    },
    planets: {},
  };

  async function render(mode: 'avkahada' | 'favourable'): Promise<HTMLElement> {
    await TestBed.configureTestingModule({
      imports: [ReferenceComponent],
      providers: [
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { snapshot: { data: { referenceMode: mode } } } },
        { provide: KundliStore, useValue: { activeId: signal('profile-1'), active: signal({ id: 'profile-1' }), load: () => Promise.resolve() } },
        { provide: VedicService, useValue: { all: () => Promise.resolve(chart) } },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(ReferenceComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    await Promise.resolve();
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  function rowsOf(section: Element): Record<string, string> {
    return Object.fromEntries(Array.from(section.querySelectorAll('.ref-row'))
      .map((row) => [row.querySelector('span')?.textContent?.trim() ?? '', row.querySelector('strong')?.textContent?.trim() ?? '']));
  }

  it('keeps the person’s own constants and the ghatak markers in separate sections', async () => {
    const el = await render('avkahada');
    const sections = Array.from(el.querySelectorAll('.ref-section'));
    const headings = sections.map((section) => section.querySelector('h2')?.textContent?.trim());
    expect(headings[0]).toBe('Chart anchors');
    expect(headings.at(-1)).toBe('Ghatak chakra');

    const anchors = rowsOf(sections[0]);
    expect(anchors['Lagna (ascendant)']).toBe('Aries (Mesha)');
    expect(anchors['Rashi (Moon sign)']).toBe('Libra (Tula)');
    expect(anchors['Janma nakshatra']).toBe('Swati');
    expect(anchors['Tithi']).toBeUndefined();

    const ghatak = rowsOf(sections.at(-1)!);
    expect(ghatak['Ghatak lagna']).toBe('Libra (Tula)');
    expect(ghatak['Ghatak Moon sign']).toBe('Capricorn (Makara)');
    expect(ghatak['Ghatak tithis']).toBe('4, 9, 14');
    expect(ghatak['Ghatak nakshatra']).toBe('Shatabhisha');
    // Unverified ghatak columns (null) are not rendered as "—" rows.
    expect(ghatak['Ghatak yoga']).toBeUndefined();
    expect(sections.at(-1)!.classList).toContain('caution');
    expect(el.textContent).not.toContain('rashi sanskrit');
  });

  it('shows both number conventions with their sources and joins lists', async () => {
    const el = await render('favourable');
    const sections = Array.from(el.querySelectorAll('.ref-section'));
    const chartNumber = rowsOf(sections[0]);
    expect(sections[0].querySelector('h2')?.textContent).toContain('Chart number');
    expect(chartNumber['Number']).toBe('9');
    expect(chartNumber['From']).toBe('Mars, the lagna lord');
    expect(chartNumber['Also agrees']).toBe('Nakshatra lord');

    const moolank = rowsOf(sections[1]);
    expect(sections[1].querySelector('h2')?.textContent).toContain('moolank');
    expect(moolank['Moolank']).toBe('6');
    expect(moolank['Good numbers']).toBe('3, 6, 9');
    expect(el.textContent).not.toContain('good numbers · 0');

    const signature = rowsOf(sections[2]);
    expect(signature['Colour']).toBe('Coral Red');
    expect(signature['Stone']).toBe('Red Coral');
  });
});
