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

/**
 * Settings > Text size: a size for Siddha alone, so a reader can make the
 * app larger or smaller without changing every other app on the phone.
 * Android applies it as the WebView's text zoom (TextSizePlugin, stored
 * natively so it is in place before the first screen draws). iOS's WebView
 * has no text zoom yet, so the row shows on Android only.
 */
@Injectable({ providedIn: 'root' })
export class TextSizeService {
  readonly available = Capacitor.getPlatform() === 'android';
  /** null until the phone answers. */
  readonly choice = signal<TextSizeChoice | null>(null);
  /** The phone's own font size, in percent, for the "Phone setting" row. */
  readonly phonePercent = signal(100);

  async load(): Promise<void> {
    if (!this.available) {
      this.choice.set(0);
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
      await TextSize.set({ percent });
    } finally {
      // The headlines divide the new zoom back out (mobile-tokens.scss).
      requestAnimationFrame(() => publishTextZoom());
    }
  }
}
