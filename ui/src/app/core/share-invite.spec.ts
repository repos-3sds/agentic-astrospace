import { INVITE_URL, shareInviteText, STORE_LINKS } from './share-invite';

describe('share invite text', () => {
  const stores = (android: boolean, ios: boolean) => ({
    android: { ...STORE_LINKS.android, live: android },
    ios: { ...STORE_LINKS.ios, live: ios },
  });

  it('asks friends to register for the test while no store is live', () => {
    const text = shareInviteText(stores(false, false));
    expect(text).toBe(`Interested in testing the Siddha app? Register yourself here: ${INVITE_URL}`);
  });

  it('gives each live store link, and drops the test invite', () => {
    const text = shareInviteText(stores(true, true));
    expect(text).toContain(`Android: ${STORE_LINKS.android.url}`);
    expect(text).toContain(`iPhone: ${STORE_LINKS.ios.url}`);
    expect(text).not.toContain('testing');
  });

  it('gives only the store that is live', () => {
    const text = shareInviteText(stores(true, false));
    expect(text).toContain('Android:');
    expect(text).not.toContain('iPhone:');
  });

  it('never points to the web checkout or prices', () => {
    for (const [a, i] of [[false, false], [true, true]] as const) {
      const text = shareInviteText(stores(a, i));
      expect(text).not.toMatch(/\/buy|₹|\$|price/i);
    }
  });
});
