import { TestBed } from '@angular/core/testing';

import { AskWeighingCardComponent } from './ask-weighing-card.component';
import { AskWeighing } from '../../../core/models';

const WEIGHING: AskWeighing = {
  angles: [
    { key: 'ashtakavarga', label: 'Ashtakavarga', plain_label: 'Planet support score', call: 'bad', weight: 2, why: 'Saturn bindus 17 in the 10th.' },
    { key: 'dasha', label: 'Dasha periods', plain_label: 'Your current time period', call: 'good', weight: 4, why: 'Jupiter period runs the 10th lord.' },
    { key: 'yogas_doshas', label: 'Yogas and doshas', plain_label: 'Special chart combinations', call: 'moderate', weight: 3, why: 'Dhana yoga holds.' },
  ],
  overall: { score: 0.8, band: 'moderately good' },
};

function render(plain: boolean): HTMLElement {
  const fixture = TestBed.createComponent(AskWeighingCardComponent);
  fixture.componentRef.setInput('weighing', WEIGHING);
  fixture.componentRef.setInput('plain', plain);
  fixture.detectChanges();
  return fixture.nativeElement as HTMLElement;
}

describe('AskWeighingCardComponent', () => {
  it('lists every angle heaviest first with its call, weight and the overall band', () => {
    const el = render(false);
    const names = Array.from(el.querySelectorAll('.angle-name')).map((n) => n.textContent?.trim());
    expect(names).toEqual(['Dasha periods', 'Yogas and doshas', 'Ashtakavarga']);
    const calls = Array.from(el.querySelectorAll('.call-pill')).map((n) => n.textContent?.trim());
    expect(calls).toEqual(['Good', 'Fairly good', 'Against']);
    expect(el.querySelector('.weight')?.getAttribute('aria-label')).toBe('Weight 4 of 5');
    expect(el.querySelectorAll('.angle-row')[0].querySelectorAll('.dot.on').length).toBe(4);
    expect(el.querySelector('.overall-band')?.textContent?.trim()).toBe('Moderately good');
    expect(el.querySelector('.overall')?.getAttribute('data-tone')).toBe('good');
    expect(el.querySelectorAll('.angle-why').length).toBe(3);
  });

  it('uses plain names and hides chart reasons in Guided', () => {
    const el = render(true);
    const names = Array.from(el.querySelectorAll('.angle-name')).map((n) => n.textContent?.trim());
    expect(names).toEqual(['Your current time period', 'Special chart combinations', 'Planet support score']);
    expect(el.querySelectorAll('.angle-why').length).toBe(0);
    expect(el.textContent).not.toContain('bindus');
    expect(el.querySelector('.overall-label')?.textContent?.trim()).toBe('All together');
  });
});
