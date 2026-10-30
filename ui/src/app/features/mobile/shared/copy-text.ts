/**
 * Puts text on the clipboard, trying the Clipboard API first and the legacy
 * execCommand path only on that API's own failure.
 *
 * The two are independent mechanisms, not a feature-detected either/or:
 * `navigator.clipboard.writeText` can exist and still reject — a common
 * shape in Capacitor/WebView contexts, where the API is present but blocked
 * by the WebView's clipboard policy or a user-activation lost through the
 * native bridge. Falling through only on rejection is what makes the
 * fallback reachable at all.
 */
export async function copyText(text: string): Promise<boolean> {
  if (!text || typeof document === 'undefined') return false;
  if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // fall through to the legacy path
    }
  }
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  let ok = false;
  try {
    ok = document.execCommand('copy');
  } catch {
    ok = false;
  }
  textarea.remove();
  return ok;
}
