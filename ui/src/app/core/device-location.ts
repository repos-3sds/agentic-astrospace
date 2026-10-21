import { Geolocation } from '@capacitor/geolocation';

/**
 * The phone's approximate position, read once when the reader taps "Use my
 * location", for finding the nearest city. Never watched, never stored: the
 * caller turns it into a city and the city is what the app keeps.
 *
 * Approximate on purpose. Sunrise moves about a minute per 15-20 km, so a
 * position good to a kilometre or two is all a timing needs, and Android
 * asks for "approximate" only because the manifest declares nothing finer.
 * Rounded to two decimals (about a kilometre) before it leaves the phone.
 */
export async function approximatePosition(): Promise<{ lat: number; lng: number }> {
  try {
    const position = await Geolocation.getCurrentPosition({
      enableHighAccuracy: false,
      timeout: 15000,
      maximumAge: 10 * 60 * 1000,
    });
    return { lat: round(position.coords.latitude), lng: round(position.coords.longitude) };
  } catch (error) {
    throw new Error(locationErrorMessage(error));
  }
}

function round(value: number): number {
  return Math.round(value * 100) / 100;
}

/** Plain words for the reader; the plugin's own messages are for developers. */
export function locationErrorMessage(error: unknown): string {
  const text = String((error as { message?: string })?.message ?? error).toLowerCase();
  if (/denied|permission|not authori[sz]ed/.test(text)) {
    return 'Location is off for Siddha. Search for your city instead, or allow location in your phone settings.';
  }
  if (/disabled|services/.test(text)) {
    return 'Location is turned off on this phone. Search for your city instead.';
  }
  return 'Could not find where you are just now. Search for your city instead.';
}
