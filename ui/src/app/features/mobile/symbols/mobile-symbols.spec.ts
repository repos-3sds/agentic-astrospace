import { directionSymbol, gemSymbol } from './mobile-symbols';

describe('mobile symbols', () => {
  it('points South-East at 135°, not at plain East', () => {
    expect(directionSymbol('South-East').angle).toBe(135);
    expect(directionSymbol('North West').angle).toBe(315);
    expect(directionSymbol('East').angle).toBe(90);
  });

  it('gives a diamond a colour that shows on a pale chip', () => {
    expect(gemSymbol('Diamond').color).not.toBe('#dbeafe');
    expect(gemSymbol('Blue Sapphire').color).toBe('#2d5bd1');
  });
});
