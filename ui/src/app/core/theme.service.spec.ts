import { TestBed } from '@angular/core/testing';

import { ThemeService } from './theme.service';

/**
 * "Dark, always" was the default until 2026-07-27: a fresh native install
 * opened dark on a phone set to light, with no way out, because /m hides the
 * web theme toggle and mobile Settings had no Appearance row. The fix was
 * deferring to the device (`prefers-color-scheme`) until the reader
 * explicitly overrides it — and, separately, making sure that override is
 * the ONLY thing ever written to storage. Persisting from the apply-effect
 * (the obvious shape) would stamp the device preference into storage on
 * first paint and permanently detach the app from the device, which is the
 * same bug wearing a different hat. These tests hold both properties.
 *
 * No component harness: ThemeService's constructor calls effect(), which
 * needs a real injector — not just an injection *context*, since effect()
 * resolves ChangeDetectionScheduler from Angular's bootstrap providers, which
 * a bare Injector.create() doesn't supply. TestBed.runInInjectionContext is
 * the minimal way to get that; nothing here compiles a template, creates a
 * fixture, or calls detectChanges.
 */
const STORAGE_KEY = 'astrospace-theme';

function fakeMatchMedia(initialMatches: boolean) {
  let listener: ((event: { matches: boolean }) => void) | null = null;
  const mediaQueryList = {
    matches: initialMatches,
    addEventListener: (_type: string, callback: (event: { matches: boolean }) => void) => {
      listener = callback;
    },
    removeEventListener: () => {},
  };
  return {
    mediaQueryList,
    fireChange(matches: boolean) {
      mediaQueryList.matches = matches;
      listener?.({ matches });
    },
  };
}

function createThemeService(): ThemeService {
  return TestBed.runInInjectionContext(() => new ThemeService());
}

describe('ThemeService', () => {
  afterEach(() => {
    localStorage.removeItem(STORAGE_KEY);
    TestBed.resetTestingModule();
  });

  describe('no stored choice', () => {
    it('follows prefers-color-scheme: dark', () => {
      localStorage.removeItem(STORAGE_KEY);
      spyOn(window, 'matchMedia').and.returnValue(fakeMatchMedia(true).mediaQueryList as unknown as MediaQueryList);

      const service = createThemeService();

      expect(service.preference()).toBe('system');
      expect(service.dark()).toBe(true);
    });

    it('follows prefers-color-scheme: light', () => {
      localStorage.removeItem(STORAGE_KEY);
      spyOn(window, 'matchMedia').and.returnValue(fakeMatchMedia(false).mediaQueryList as unknown as MediaQueryList);

      const service = createThemeService();

      expect(service.preference()).toBe('system');
      expect(service.dark()).toBe(false);
    });

    it('keeps following the device live, until overridden', () => {
      localStorage.removeItem(STORAGE_KEY);
      const fake = fakeMatchMedia(false);
      spyOn(window, 'matchMedia').and.returnValue(fake.mediaQueryList as unknown as MediaQueryList);
      const service = createThemeService();
      expect(service.dark()).toBe(false);

      fake.fireChange(true);
      expect(service.dark()).toBe(true);

      fake.fireChange(false);
      expect(service.dark()).toBe(false);
    });
  });

  describe('an explicit choice', () => {
    it('is read back from storage on construction', () => {
      localStorage.setItem(STORAGE_KEY, 'dark');
      spyOn(window, 'matchMedia').and.returnValue(fakeMatchMedia(false).mediaQueryList as unknown as MediaQueryList);

      const service = createThemeService();

      expect(service.preference()).toBe('dark');
      expect(service.dark()).toBe(true); // device says light; the explicit choice wins
    });

    it('stops following live device changes', () => {
      localStorage.setItem(STORAGE_KEY, 'light');
      const fake = fakeMatchMedia(false);
      spyOn(window, 'matchMedia').and.returnValue(fake.mediaQueryList as unknown as MediaQueryList);
      const service = createThemeService();
      expect(service.dark()).toBe(false);

      fake.fireChange(true); // device flips to dark; explicit "light" must not move

      expect(service.dark()).toBe(false);
      expect(service.preference()).toBe('light');
    });
  });

  describe('storage holds explicit choices only', () => {
    beforeEach(() => {
      spyOn(window, 'matchMedia').and.returnValue(fakeMatchMedia(false).mediaQueryList as unknown as MediaQueryList);
    });

    it('setPreference("dark") / ("light") write the literal string', () => {
      const service = createThemeService();

      service.setPreference('dark');
      expect(localStorage.getItem(STORAGE_KEY)).toBe('dark');

      service.setPreference('light');
      expect(localStorage.getItem(STORAGE_KEY)).toBe('light');
    });

    it('setPreference("system") removes the key rather than storing the word "system"', () => {
      const service = createThemeService();
      service.setPreference('dark');
      expect(localStorage.getItem(STORAGE_KEY)).not.toBeNull();

      service.setPreference('system');

      // The regression this guards: storing the literal string "system"
      // would still *work* today, but it freezes in whatever the device
      // preference happened to be at the moment of the call, rather than
      // continuing to track it — indistinguishable from the original bug
      // until the reader's OS theme changes next.
      expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
    });

    it('toggle() persists an explicit choice, never "system"', () => {
      localStorage.removeItem(STORAGE_KEY);
      const service = createThemeService(); // system, light-by-device

      service.toggle();

      expect(service.preference()).toBe('dark');
      expect(localStorage.getItem(STORAGE_KEY)).toBe('dark');
    });
  });
});
