import { Injectable, effect, signal } from '@angular/core';

const STORAGE_KEY = 'astrospace-theme';

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
function preferredTheme(): boolean {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === 'dark' || stored === 'light' ? stored === 'dark' : prefersDark();
}

@Injectable({ providedIn: 'root' })
export class ThemeService {
  readonly dark = signal(preferredTheme());

  constructor() {
    // Applies the theme; deliberately does NOT persist. Storage holds explicit
    // choices only — writing here would stamp the device's preference into
    // storage on first paint and permanently detach the app from the device.
    effect(() => {
      document.documentElement.classList.toggle('app-dark', this.dark());
    });

    // Follow the device until the reader overrides it.
    if (typeof matchMedia === 'function') {
      matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (event) => {
        if (!localStorage.getItem(STORAGE_KEY)) {
          this.dark.set(event.matches);
        }
      });
    }
  }

  /** The only thing that writes storage: an explicit choice by the reader. */
  toggle(): void {
    this.dark.update((v) => !v);
    localStorage.setItem(STORAGE_KEY, this.dark() ? 'dark' : 'light');
  }
}
