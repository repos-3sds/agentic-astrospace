import { Injectable, effect, signal } from '@angular/core';
import { Capacitor, SystemBars, SystemBarsStyle } from '@capacitor/core';

const STORAGE_KEY = 'astrospace-theme';
export type ThemePreference = 'system' | 'light' | 'dark';

function prefersDark(): boolean {
  return typeof matchMedia === 'function'
    && matchMedia('(prefers-color-scheme: dark)').matches;
}

/**
 * What the app opens as when nobody has chosen yet.
 *
 * Previously this was "dark, always" — `localStorage !== 'light'`. On the web
 * that is merely opinionated; in the native app it is a bug you cannot escape,
 * because /m hides the web theme toggle and mobile Settings has no Appearance
 * row. A fresh install opened dark on a phone set to light, with no way out.
 *
 * Deferring to the device is the honest default: the reader has already told
 * their phone which they want.
 */
function storedPreference(): ThemePreference {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === 'dark' || stored === 'light' ? stored : 'system';
}

@Injectable({ providedIn: 'root' })
export class ThemeService {
  readonly preference = signal<ThemePreference>(storedPreference());
  readonly dark = signal(
    this.preference() === 'system' ? prefersDark() : this.preference() === 'dark',
  );

  constructor() {
    effect(() => {
      const dark = this.dark();
      document.documentElement.classList.toggle('app-dark', dark);
      void this.applyNativeBars(dark);
    });
    effect(() => void this.shareWithLaunchScreen(this.preference()));

    // Follow the device until the reader overrides it.
    if (typeof matchMedia === 'function') {
      matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (event) => {
        if (this.preference() === 'system') {
          this.dark.set(event.matches);
        }
      });
    }
  }

  /** The only thing that writes storage: an explicit choice by the reader. */
  toggle(): void {
    this.setPreference(this.dark() ? 'light' : 'dark');
  }

  setPreference(preference: ThemePreference): void {
    this.preference.set(preference);
    this.dark.set(preference === 'system' ? prefersDark() : preference === 'dark');
    if (preference === 'system') {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, preference);
    }
  }

  /**
   * Android draws its launch screen before the WebView exists, in the phone's
   * light or dark, not the app's: a light-themed app on a dark phone opened
   * on black, then faded to the ivory splash. MainActivity reads this key
   * (Capacitor Preferences, same name) and tells Android the app's mode.
   */
  private async shareWithLaunchScreen(preference: ThemePreference): Promise<void> {
    if (Capacitor.getPlatform() !== 'android') return;
    try {
      const { Preferences } = await import('@capacitor/preferences');
      await Preferences.set({ key: STORAGE_KEY, value: preference });
    } catch {
      // The launch screen then follows the phone, as before.
    }
  }

  private async applyNativeBars(dark: boolean): Promise<void> {
    if (!Capacitor.isNativePlatform()) return;
    try {
      // SystemBars styles the status bar and Android's navigation bar
      // together; StatusBar left the nav-bar buttons dark on the dark theme.
      // The app draws edge to edge, so there is no bar colour to set (N10).
      await SystemBars.setStyle({ style: dark ? SystemBarsStyle.Dark : SystemBarsStyle.Light });
    } catch {
      // Native chrome should never block theme application.
    }
  }
}
