import { SessionStorageAdapter, migratingSecureStorage } from './session-storage';

function memoryStorage(seed: Record<string, string> = {}): SessionStorageAdapter & { data: Map<string, string> } {
  const data = new Map(Object.entries(seed));
  return {
    data,
    getItem: async (key) => data.get(key) ?? null,
    setItem: async (key, value) => { data.set(key, value); },
    removeItem: async (key) => { data.delete(key); },
  };
}

/**
 * Until 2026-10-15 the Supabase session sat in @capacitor/preferences
 * (UserDefaults / SharedPreferences). Moving it to the keychain must not sign
 * existing users out, and must not leave the old plaintext copy behind.
 */
describe('migratingSecureStorage', () => {
  const KEY = 'sb-abc-auth-token';

  it('reads from secure storage first', async () => {
    const secure = memoryStorage({ [KEY]: 'secure-session' });
    const legacy = memoryStorage({ [KEY]: 'old-session' });

    expect(await migratingSecureStorage(secure, legacy).getItem(KEY)).toBe('secure-session');
    expect(legacy.data.get(KEY)).toBe('old-session');
  });

  it('moves a session left in Preferences into secure storage and deletes the original', async () => {
    const secure = memoryStorage();
    const legacy = memoryStorage({ [KEY]: 'old-session' });

    expect(await migratingSecureStorage(secure, legacy).getItem(KEY)).toBe('old-session');
    expect(secure.data.get(KEY)).toBe('old-session');
    expect(legacy.data.has(KEY)).toBeFalse();
  });

  it('returns null when neither store has the key', async () => {
    expect(await migratingSecureStorage(memoryStorage(), memoryStorage()).getItem(KEY)).toBeNull();
  });

  it('writes only to secure storage and removes from both', async () => {
    const secure = memoryStorage();
    const legacy = memoryStorage({ [KEY]: 'old-session' });
    const storage = migratingSecureStorage(secure, legacy);

    await storage.setItem(KEY, 'fresh');
    expect(secure.data.get(KEY)).toBe('fresh');
    expect(legacy.data.get(KEY)).toBe('old-session');

    await storage.removeItem(KEY);
    expect(secure.data.has(KEY)).toBeFalse();
    expect(legacy.data.has(KEY)).toBeFalse();
  });
});
