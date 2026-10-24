/**
 * Android's font-size setting scales every piece of WebView text
 * (MainActivity.capTextZoom caps it at 115%). Reading text should follow it;
 * the big display type should not, because it is already large and was the
 * first thing to crowd a 360-wide phone. Measure the zoom once and publish it
 * as --text-zoom, which the display mixins in mobile-tokens.scss divide back
 * out. A font-size change recreates the activity, so once is enough.
 */
export function measureTextZoom(): number {
  if (typeof document === 'undefined' || !document.body) return 1;
  const probe = document.createElement('span');
  probe.style.cssText = 'position:absolute;visibility:hidden;font-size:100px;line-height:1;';
  probe.textContent = 'M';
  document.body.appendChild(probe);
  const zoom = probe.getBoundingClientRect().height / 100;
  probe.remove();
  return zoom > 0.5 && zoom < 2.5 ? zoom : 1;
}

export function publishTextZoom(): void {
  const zoom = measureTextZoom();
  if (Math.abs(zoom - 1) > 0.02) {
    document.documentElement.style.setProperty('--text-zoom', zoom.toFixed(3));
  }
}
