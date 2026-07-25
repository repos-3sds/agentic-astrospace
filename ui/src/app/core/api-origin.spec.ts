import { Capacitor } from '@capacitor/core';

import { apiOrigin, apiUrl } from './api-origin';
import { environment } from '../../environments/environment';

/**
 * These guard a failure that is invisible until the app runs on a device: a
 * relative API path resolves inside the Capacitor bundle, so every request
 * 404s with nothing in the network log to explain it.
 */
describe('apiOrigin', () => {
  let native: jasmine.Spy;

  beforeEach(() => {
    native = spyOn(Capacitor, 'isNativePlatform');
  });

  afterEach(() => {
    environment.nativeApiOrigin = '';
  });

  it('stays relative on the web so same-origin deployment is unchanged', () => {
    native.and.returnValue(false);
    expect(apiOrigin()).toBe('');
    expect(apiUrl('/api/v1/kundlis')).toBe('/api/v1/kundlis');
  });

  it('is absolute on native', () => {
    native.and.returnValue(true);
    environment.nativeApiOrigin = 'https://api.example.com';
    expect(apiUrl('/api/v1/kundlis')).toBe('https://api.example.com/api/v1/kundlis');
  });

  it('does not double the slash when the origin has a trailing one', () => {
    native.and.returnValue(true);
    environment.nativeApiOrigin = 'https://api.example.com/';
    expect(apiUrl('/api/v1/kundlis')).toBe('https://api.example.com/api/v1/kundlis');
  });

  it('fails loudly on native when the origin was never configured', () => {
    // Better here than as an unexplained 404 on a tester's phone.
    native.and.returnValue(true);
    environment.nativeApiOrigin = '';
    expect(() => apiOrigin()).toThrowError(/nativeApiOrigin is not configured/);
  });

  it('ignores a missing native origin on the web', () => {
    native.and.returnValue(false);
    environment.nativeApiOrigin = '';
    expect(() => apiOrigin()).not.toThrow();
  });
});
