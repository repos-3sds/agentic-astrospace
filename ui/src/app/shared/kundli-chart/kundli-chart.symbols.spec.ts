import { TestBed } from '@angular/core/testing';

import { PlanetConditionAnnotation, VargaChart } from '../../core/models';
import { KundliChartComponent } from './kundli-chart.component';

const D1_SYMBOLS: Record<string, PlanetConditionAnnotation[]> = {
  Venus: [{ code: 'debilitated', symbol: '↓', label: 'Debilitated', tone: 'bad' }],
  Mercury: [{ code: 'combust', symbol: '☼', label: 'Combust', tone: 'warn' }],
};

function render(chart: VargaChart): Record<string, string> {
  const fixture = TestBed.createComponent(KundliChartComponent);
  fixture.componentRef.setInput('chart', chart);
  fixture.componentRef.setInput('chartStyle', 'south');
  fixture.componentRef.setInput('annotations', D1_SYMBOLS);
  fixture.detectChanges();
  const out: Record<string, string> = {};
  for (const hit of Array.from(fixture.nativeElement.querySelectorAll('g.planet-hit')) as Element[]) {
    const symbols = Array.from(hit.querySelectorAll('tspan.condition-symbol')).map((t) => t.textContent?.trim());
    out[hit.getAttribute('aria-label') ?? ''] = symbols.join('');
  }
  return out;
}

describe('KundliChartComponent symbols per chart', () => {
  it('draws the varga’s own symbols, not the D1 ones passed in', () => {
    const d9 = {
      name: 'Navamsha', signifies: '', verified_rule: true, lagna: { sign: 'Gemini' },
      planets: {
        Venus: { sign: 'Capricorn', house: 8, annotations: [] },
        Mercury: {
          sign: 'Pisces', house: 10, retrograde: true,
          annotations: [
            { code: 'debilitated', symbol: '↓', label: 'Debilitated', tone: 'bad' },
            { code: 'retrograde', symbol: '↺', label: 'Retrograde', tone: 'neutral' },
          ],
        },
        Mars: { sign: 'Libra', house: 5, vargottama: true, annotations: [] },
      },
    } as unknown as VargaChart;
    const symbols = render(d9);
    expect(symbols['Venus']).toBe('');
    expect(symbols['Mercury']).toBe('↓↺');
    expect(symbols['Mars']).toBe('✦');
  });

  it('still uses the passed symbols for a chart without its own', () => {
    const old = {
      name: 'Rashi', signifies: '', verified_rule: true, lagna: { sign: 'Leo' },
      planets: { Venus: { sign: 'Virgo', house: 2 }, Mercury: { sign: 'Cancer', house: 12, retrograde: true } },
    } as unknown as VargaChart;
    const symbols = render(old);
    expect(symbols['Venus']).toBe('↓');
    expect(symbols['Mercury']).toBe('↺☼');
  });
});
