import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

import { PreferencesService } from './preferences.service';

describe('PreferencesService usage sharing', () => {
  afterEach(() => localStorage.removeItem('astrospace-preferences'));

  const load = () => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    return TestBed.inject(PreferencesService);
  };

  it('is off for a new reader', () => {
    localStorage.removeItem('astrospace-preferences');
    expect(load().shareUsage()).toBeFalse();
  });

  it('treats the old default of on as not yet answered', () => {
    localStorage.setItem('astrospace-preferences', JSON.stringify({ shareUsage: true }));
    expect(load().shareUsage()).toBeFalse();
  });

  it('keeps an answer the reader gave', () => {
    localStorage.setItem('astrospace-preferences', JSON.stringify({ shareUsage: true, usageAsked: true }));
    expect(load().shareUsage()).toBeTrue();
  });
});
