import { Injectable, effect, signal } from '@angular/core';

const STORAGE_KEY = 'astrospace-theme';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  /** dark mode is the default look */
  readonly dark = signal(localStorage.getItem(STORAGE_KEY) !== 'light');

  constructor() {
    effect(() => {
      const dark = this.dark();
      document.documentElement.classList.toggle('app-dark', dark);
      localStorage.setItem(STORAGE_KEY, dark ? 'dark' : 'light');
    });
  }

  toggle(): void {
    this.dark.update((v) => !v);
  }
}
