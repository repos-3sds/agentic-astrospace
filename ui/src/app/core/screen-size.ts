import { Signal, signal } from '@angular/core';

/**
 * The native app's layout follows the window, not the device: an iPad in
 * Split View or an Android tablet in multi-window gets whatever fits the space
 * it has. Keep these in step with the media queries in mobile-tokens.scss
 * ($m-tablet, $m-wide).
 *
 * - under 600: phone, bottom tab bar, one column (unchanged)
 * - 600 and up: tablet, side rail, reading column
 * - 900 and up: wide tablet, side rail plus two panes where they help
 */
export const TABLET_MIN_WIDTH = 600;
export const WIDE_MIN_WIDTH = 900;

function mediaSignal(query: string): Signal<boolean> {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return signal(false);
  const media = window.matchMedia(query);
  const value = signal(media.matches);
  media.addEventListener?.('change', (event) => value.set(event.matches));
  return value.asReadonly();
}

let tablet: Signal<boolean> | null = null;
let wide: Signal<boolean> | null = null;

/** True while the window is at least tablet width (side rail instead of tabs). */
export function tabletLayout(): Signal<boolean> {
  return (tablet ??= mediaSignal(`(min-width: ${TABLET_MIN_WIDTH}px)`));
}

/** True while the window is wide enough for two panes side by side. */
export function wideLayout(): Signal<boolean> {
  return (wide ??= mediaSignal(`(min-width: ${WIDE_MIN_WIDTH}px)`));
}
