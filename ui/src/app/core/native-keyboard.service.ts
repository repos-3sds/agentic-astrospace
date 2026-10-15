import { Injectable } from '@angular/core';
import { Capacitor } from '@capacitor/core';

/** Set on <body> while the on-screen keyboard is up (native only). */
export const KEYBOARD_OPEN_CLASS = 'as-keyboard-open';

/**
 * The native keyboard, via @capacitor/keyboard.
 *
 * capacitor.config.ts has iOS resize the whole WebView (`resize: 'native'`),
 * and on Android 15+ Capacitor 8's SystemBars pads the WebView by the IME
 * inset, so on both platforms the page itself gets shorter rather than being
 * overlapped. What is left to the web side:
 *
 * - hide the iOS accessory bar (prev/next/done), which only duplicates the
 *   app's own controls on short forms;
 * - mark the body while the keyboard is up, so the floating tab bar steps
 *   aside instead of riding on top of the keyboard (styles-mobile.scss).
 *
 * The plugin is imported lazily: the web build never loads it.
 */
@Injectable({ providedIn: 'root' })
export class NativeKeyboardService {
  private handles: { remove: () => Promise<void> | void }[] = [];
  private installed = false;

  async install(): Promise<void> {
    if (this.installed || !Capacitor.isNativePlatform()) return;
    this.installed = true;
    try {
      const { Keyboard } = await import('@capacitor/keyboard');
      if (Capacitor.getPlatform() === 'ios') {
        await Keyboard.setAccessoryBarVisible({ isVisible: false }).catch(() => undefined);
      }
      const open = () => document.body.classList.add(KEYBOARD_OPEN_CLASS);
      const close = () => document.body.classList.remove(KEYBOARD_OPEN_CLASS);
      // "Will" events so the tab bar is gone before the keyboard animates in;
      // Android only reliably sends the "did" pair, so listen to both.
      this.handles = await Promise.all([
        Keyboard.addListener('keyboardWillShow', open),
        Keyboard.addListener('keyboardDidShow', open),
        Keyboard.addListener('keyboardWillHide', close),
        Keyboard.addListener('keyboardDidHide', close),
      ]);
    } catch {
      // Plugin missing from a stale native build: the app works, the tab bar
      // just stays put while typing.
      this.installed = false;
    }
  }

  uninstall(): void {
    for (const handle of this.handles) void handle.remove();
    this.handles = [];
    this.installed = false;
    if (typeof document !== 'undefined') document.body.classList.remove(KEYBOARD_OPEN_CLASS);
  }
}
