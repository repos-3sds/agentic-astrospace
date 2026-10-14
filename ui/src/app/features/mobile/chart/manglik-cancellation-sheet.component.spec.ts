import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ManglikPayload } from '../../../core/models';
import { ManglikCancellationSheetComponent } from './manglik-cancellation-sheet.component';

/**
 * The sheet used to be a fixed Figma transcript telling every user their
 * Manglik was cancelled by "Mars in Scorpio". These specs pin the three
 * outcomes the engine actually returns so the sheet can never again show
 * evidence the chart does not contain.
 */
function manglik(overrides: Partial<ManglikPayload>): ManglikPayload {
  return {
    name: 'Manglik / Kuja Dosha',
    active: true,
    severity: 'moderate',
    net_severity: 'moderate',
    active_references: ['Lagna', 'Venus'],
    checks: [
      { reference: 'Lagna', house: 7, active: true, mars_sign: 'Capricorn', reference_sign: 'Cancer' },
      { reference: 'Moon', house: 3, active: false, mars_sign: 'Capricorn', reference_sign: 'Scorpio' },
      { reference: 'Venus', house: 12, active: true, mars_sign: 'Capricorn', reference_sign: 'Aquarius' },
    ],
    exceptions: [
      { rule: 'Mars in own sign (Aries, Scorpio) or exalted (Capricorn)', applies: false, detail: 'Mars in Capricorn — neither own sign nor exalted.' },
      { rule: 'Jupiter aspects Mars (graha drishti 5/7/9)', applies: false, detail: 'Jupiter in Gemini is 6 signs from Mars; no drishti.' },
      { rule: 'Mars conjunct Moon in the same sign', applies: false, detail: 'Mars in Capricorn, Moon in Scorpio; not conjunct.' },
    ],
    rule: 'Mars in houses 1, 2, 4, 7, 8, or 12 from Lagna, Moon, or Venus.',
    verified: true,
    source_status: 'convention_dependent',
    notes: ['No cancellation/exception rule applies; net_severity equals severity.'],
    ...overrides,
  };
}

describe('ManglikCancellationSheetComponent', () => {
  let fixture: ComponentFixture<ManglikCancellationSheetComponent>;

  function render(payload: ManglikPayload): HTMLElement {
    fixture = TestBed.createComponent(ManglikCancellationSheetComponent);
    fixture.componentRef.setInput('manglik', payload);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [ManglikCancellationSheetComponent] });
  });

  it('says the flag stands when the dosha is active and no exception applies', () => {
    const host = render(manglik({}));
    const text = host.textContent ?? '';
    expect(fixture.componentInstance.state()).toBe('stands');
    expect(text).toContain('FLAG, MODERATE');
    expect(text).toContain('Why this Manglik flag stands');
    expect(text).toContain('Mars is in Capricorn');
    expect(text).toContain('House 7 from Lagna');
    expect(text).toContain('House 12 from Venus');
    expect(text).not.toContain('House 3 from Moon');
    expect(text).toContain('Exceptions checked — none applies');
    expect(text).not.toContain('Exception met');
    expect(text).not.toContain('cancelled');
    expect(text).not.toContain('Scorpio, one of its own signs');
  });

  it('shows the applied exception and the downgraded net severity when one applies', () => {
    const host = render(manglik({
      severity: 'moderate',
      net_severity: 'mild',
      exceptions: [
        { rule: 'Mars in own sign (Aries, Scorpio) or exalted (Capricorn)', applies: true, detail: 'Mars in Capricorn — exalted; dosha weakened.' },
        { rule: 'Jupiter aspects Mars (graha drishti 5/7/9)', applies: false, detail: 'No drishti.' },
      ],
      notes: ['Exception rules applied (convention-dependent): Mars in own sign (Aries, Scorpio) or exalted (Capricorn). Raw severity is kept.'],
    }));
    const text = host.textContent ?? '';
    expect(fixture.componentInstance.state()).toBe('weakened');
    expect(text).toContain('FLAG, WEAKENED TO MILD');
    expect(text).toContain('Exception met: Mars in own sign');
    expect(text).toContain('exalted; dosha weakened');
    expect(text).toContain('Also checked');
    expect(text).toContain('convention-dependent');
    // The engine never cancels outright, so neither does the copy.
    expect(text.toLowerCase()).not.toContain('cancelled');
  });

  it('reports no flag when the dosha is not active, and never fabricates an exception', () => {
    const host = render(manglik({
      active: false,
      severity: 'none',
      net_severity: 'none',
      active_references: [],
      checks: [
        { reference: 'Lagna', house: 3, active: false, mars_sign: 'Capricorn', reference_sign: 'Scorpio' },
        { reference: 'Moon', house: 5, active: false, mars_sign: 'Capricorn', reference_sign: 'Virgo' },
        { reference: 'Venus', house: 6, active: false, mars_sign: 'Capricorn', reference_sign: 'Leo' },
      ],
      exceptions: [
        { rule: 'Mars in own sign (Aries, Scorpio) or exalted (Capricorn)', applies: true, detail: 'Mars in Capricorn — exalted; dosha weakened.' },
      ],
    }));
    const text = host.textContent ?? '';
    expect(fixture.componentInstance.state()).toBe('not-present');
    expect(text).toContain('NOT PRESENT');
    expect(text).toContain('No Manglik flag in this chart');
    expect(text).not.toContain('WHERE MARS SITS');
    expect(text).not.toContain('Also checked');
  });
});
