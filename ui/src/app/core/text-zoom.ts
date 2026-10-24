/**
 * Android's font-size setting scales every piece of WebView text
 * (MainActivity.applyTextZoom: the phone's setting up to 102%, or the size
 * chosen in Settings > Text size). Reading text should follow it; the big
 * display type should not, because it is already large and was the first
 * thing to crowd a 360-wide phone. Measure the zoom and publish it as
 * --text-zoom, which the display mixins in mobile-tokens.scss divide back out.
 * A phone font change recreates the activity; Settings > Text size calls
 * publishTextZoom() again after changing it.
 */
let current = 1;

export function measureTextZoom(): number {
  if (typeof document === 'undefined' || !document.body) return 1;
  const probe = document.createElement('span');
  probe.setAttribute('data-text-zoom-probe', '');
  probe.style.cssText = 'position:absolute;visibility:hidden;font-size:100px;line-height:1;';
  probe.textContent = 'M';
  document.body.appendChild(probe);
  const zoom = probe.getBoundingClientRect().height / 100;
  probe.remove();
  return zoom > 0.5 && zoom < 2.5 ? zoom : 1;
}

export function publishTextZoom(): number {
  current = measureTextZoom();
  const root = document.documentElement.style;
  if (Math.abs(current - 1) > 0.02) {
    root.setProperty('--text-zoom', current.toFixed(3));
  } else {
    root.removeProperty('--text-zoom');
  }
  return current;
}

/** The zoom as last published, for code that sizes text itself (charts). */
export function currentTextZoom(): number {
  return current;
}
