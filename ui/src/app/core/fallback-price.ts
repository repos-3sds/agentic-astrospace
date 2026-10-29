/**
 * The price to show when the store has not given one: before it answers, and
 * on iPhone until App Store purchases are set up. Rupees for readers in India,
 * US dollars everywhere else, the same split as Google Play and the website
 * (`firebase-public/js/prices.js`).
 *
 * India is read from the device's time zone, so there is no location prompt.
 * The language setting is ignored: an Indian living abroad pays the dollar price.
 */
export function inIndia(zone = deviceTimeZone()): boolean {
  return zone === 'Asia/Kolkata' || zone === 'Asia/Calcutta';
}

export function fallbackPrice(inr: number, usd: number | undefined, zone = deviceTimeZone()): string {
  if (usd == null || inIndia(zone)) return `₹${inr.toLocaleString('en-IN')}`;
  return `$${usd.toFixed(2)}`;
}

function deviceTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone ?? '';
  } catch {
    return '';
  }
}
