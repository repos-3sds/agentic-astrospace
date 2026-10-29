import { fallbackPrice, inIndia } from './fallback-price';

describe('fallbackPrice', () => {
  it('shows rupees on an Indian clock', () => {
    expect(fallbackPrice(1000, 24.99, 'Asia/Kolkata')).toBe('₹1,000');
    expect(fallbackPrice(50, 2.99, 'Asia/Calcutta')).toBe('₹50');
  });

  it('shows dollars everywhere else, Canada included', () => {
    expect(fallbackPrice(300, 9.99, 'America/Toronto')).toBe('$9.99');
    expect(fallbackPrice(130, 6.99, 'America/Vancouver')).toBe('$6.99');
    expect(fallbackPrice(300, 9.99, 'Asia/Singapore')).toBe('$9.99');
  });

  it('keeps rupees when the server sent no dollar price', () => {
    expect(fallbackPrice(300, undefined, 'America/Toronto')).toBe('₹300');
  });

  it('reads only the time zone', () => {
    expect(inIndia('Asia/Kolkata')).toBeTrue();
    expect(inIndia('Asia/Dubai')).toBeFalse();
    expect(inIndia('')).toBeFalse();
  });
});
