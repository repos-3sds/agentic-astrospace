/**
 * The line that travels with a shared verse, so a friend who likes it can
 * find the app.
 *
 * While Siddha is in testing it asks people to request an invite on the
 * website's invite section. When a store listing goes public, set that
 * store's `live` to true here and the same shares carry the store link
 * instead. One flip per store; nothing else changes.
 *
 * Only the homepage's invite section and the store pages are linked: never
 * /buy or prices, which app stores do not allow an app to point to.
 */
export const STORE_LINKS = {
  android: { live: false, url: 'https://play.google.com/store/apps/details?id=app.asksiddha.mobile' },
  ios: { live: false, url: 'https://apps.apple.com/app/id6827191709' },
} as const;

export const INVITE_URL = 'https://asksiddha.app/#invite';

type StoreLinks = { [K in keyof typeof STORE_LINKS]: { live: boolean; url: string } };

/**
 * The invite or download text. Both live stores are listed whatever phone the
 * sharer has, because the friend receiving it may have the other kind.
 */
export function shareInviteText(stores: StoreLinks = STORE_LINKS): string {
  const lines: string[] = [];
  if (stores.android.live) lines.push(`Android: ${stores.android.url}`);
  if (stores.ios.live) lines.push(`iPhone: ${stores.ios.url}`);
  if (lines.length === 0) return `Interested in testing the Siddha app? Register yourself here: ${INVITE_URL}`;
  return ['Get the Siddha app:', ...lines].join('\n');
}
