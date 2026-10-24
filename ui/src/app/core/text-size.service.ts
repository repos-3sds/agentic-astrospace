import { Injectable, signal } from '@angular/core';
import { Capacitor, registerPlugin } from '@capacitor/core';
import { publishTextZoom } from './text-zoom';

interface TextSizePlugin {
  get(): Promise<{ percent: number; phonePercent: number }>;
  set(options: { percent: number }): Promise<{ percent: number }>;
}

const TextSize = registerPlugin<TextSizePlugin>('TextSize');

/** 0 follows the phone's font size (up to 102%); anything else is the reader's own size. */
export type TextSizeChoice = 0 | 90 | 100 | 115 | 130;

const IOS_KEY = 'siddha_text_size';
const CHOICES: readonly number[] = [0, 90, 100, 115, 130];

function storedIosChoice(): TextSizeChoice {
  try {
    const value = Number(localStorage.getItem(IOS_KEY));
    return (CHOICES.includes(value) ? value : 0) as TextSizeChoice;
  } catch {
    return 0;
  }
}

function applyIosTextSize(percent: TextSizeChoice): void {
  // On body, because styles.scss pins body to 100% and the property inherits.
  const body = document.body?.style as (CSSStyleDeclaration & { webkitTextSizeAdjust?: string }) | undefined;
  if (body) body.webkitTextSizeAdjust = `${percent || 100}%`;
}

/**
 * Applies the iPhone reader's saved size before the first screen draws
 * (main.ts calls it ahead of publishTextZoom). Android needs nothing here:
 * MainActivity applies its stored size natively.
 */
export function applySavedTextSize(): void {
  if (Capacitor.getPlatform() === 'ios') applyIosTextSize(storedIosChoice());
}

/**
 * Settings > Text size: a size for Siddha alone, so a reader can make the
 * app larger or smaller without changing every other app on the phone.
 * Android applies it as the WebView's text zoom (TextSizePlugin, stored
 * natively so it is in place before the first screen draws). iOS's WebView
 * has no text zoom and ignores the phone's Dynamic Type, so there it is
 * -webkit-text-size-adjust on body, saved in localStorage; "Same as phone"
 * is the design size there.
 */
@Injectable({ providedIn: 'root' })
export class TextSizeService {
  private readonly platform = Capacitor.getPlatform();
  readonly available = this.platform === 'android' || this.platform === 'ios';
  /** Only Android tells the app the phone's own font size. */
  readonly readsPhone = this.platform === 'android';
  /** null until the phone answers. */
  readonly choice = signal<TextSizeChoice | null>(null);
  /** The phone's own font size, in percent, for the "Phone setting" row. */
  readonly phonePercent = signal(100);

  async load(): Promise<void> {
    if (!this.available) {
      this.choice.set(0);
      return;
    }
    if (this.platform === 'ios') {
      this.choice.set(storedIosChoice());
      return;
    }
    try {
      const { percent, phonePercent } = await TextSize.get();
      this.choice.set(percent as TextSizeChoice);
      this.phonePercent.set(phonePercent);
    } catch {
      this.choice.set(0);
    }
  }

  async set(percent: TextSizeChoice): Promise<void> {
    this.choice.set(percent);
    if (!this.available) return;
    try {
      if (this.platform === 'ios') {
        applyIosTextSize(percent);
        try { localStorage.setItem(IOS_KEY, String(percent)); } catch { /* applies for this launch only */ }
        return;
      }
      await TextSize.set({ percent });
    } finally {
      // The headlines divide the new zoom back out (mobile-tokens.scss).
      requestAnimationFrame(() => publishTextZoom());
    }
  }
}
