import { TODAY_DRILL_DOWNS, whyDrillDowns } from './drill-downs';

describe('whyDrillDowns', () => {
  it('links the factors in the order the evidence names them, then the birth chart', () => {
    const links = whyDrillDowns(['Saturn transit over the natal Moon', 'Venus antardasha in Jupiter mahadasha']);
    expect(links.map((l) => l.route.join('/'))).toEqual(['/m/transits', '/m/chart/periods', '/m/chart']);
  });

  it('caps at three and never repeats a screen', () => {
    const links = whyDrillDowns(['Gajakesari yoga', 'Navamsa lagna', 'Shadbala of Mars', 'dasha of Rahu', 'transit']);
    expect(links.length).toBe(3);
    expect(new Set(links.map((l) => l.route.join('/'))).size).toBe(3);
  });

  it('puts what a reading is built from first, then the evidence, then the birth chart', () => {
    expect(whyDrillDowns(['Routed to Career'], TODAY_DRILL_DOWNS).map((l) => l.label))
      .toEqual(['Your life period', 'Today’s transits', 'Your birth chart']);
    expect(whyDrillDowns(['Gajakesari yoga'], TODAY_DRILL_DOWNS.slice(0, 1)).map((l) => l.label))
      .toEqual(['Your life period', 'Yogas & doshas', 'Your birth chart']);
    expect(whyDrillDowns([]).map((l) => l.label)).toEqual(['Your birth chart']);
  });
});
