import { locationErrorMessage } from './device-location';

describe('locationErrorMessage', () => {
  it('points a refused permission to the city search and phone settings', () => {
    expect(locationErrorMessage(new Error('Location permission was denied'))).toContain('allow location in your phone settings');
  });

  it('names location services being off', () => {
    expect(locationErrorMessage(new Error('Location services are not enabled'))).toContain('turned off on this phone');
  });

  it('falls back to plain words for anything else', () => {
    expect(locationErrorMessage(new Error('Timeout expired'))).toBe('Could not find where you are just now. Search for your city instead.');
  });
});
