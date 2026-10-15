import { Capacitor } from '@capacitor/core';
import { Preferences } from '@capacitor/preferences';
import { SecureStoragePlugin } from 'capacitor-secure-storage-plugin';

/**
 * Where supabase-js keeps the signed-in session (access + refresh token).
 *
 * The adapter shape is the one supabase-js accepts as `auth.storage`, so the
 * client reads and writes through it directly and nothing else in the app
 * needs to know where the tokens live.
 */
export interface SessionStorageAdapter {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
  removeItem(key: string): Promise<void>;
}

/**
 * `@capacitor/preferences` is UserDefaults on iOS and SharedPreferences on
 * Android (localStorage on the web): plaintext on disk, readable by anything
 * with filesystem access to the app sandbox, and copied into device backups.
 * Fine for public config such as the Supabase URL; never for a refresh token.
 * Until 2026-10-15 the session lived here.
 */
export const preferencesStorage: SessionStorageAdapter = {
  async getItem(key) {
    const { value } = await Preferences.get({ key });
    return value;
  },
  async setItem(key, value) {
    await Preferences.set({ key, value });
  },
  async removeItem(key) {
    await Preferences.remove({ key });
  },
};

/**
 * Keychain on iOS, Keystore-wrapped on Android (capacitor-secure-storage-plugin).
 * The plugin rejects a `get` for a key that was never written, which the
 * supabase-js contract treats as "no session", hence the catch.
 */
export const keychainStorage: SessionStorageAdapter = {
  async getItem(key) {
    try {
      const { value } = await SecureStoragePlugin.get({ key });
      return value ?? null;
    } catch {
      return null;
    }
  },
  async setItem(key, value) {
    await SecureStoragePlugin.set({ key, value });
  },
  async removeItem(key) {
    try {
      await SecureStoragePlugin.remove({ key });
    } catch {
      // Already absent; removing it twice is not an error worth surfacing.
    }
  },
};

/**
 * Keychain/Keystore storage that also carries over a session the previous
 * build left in Preferences, so upgrading does not sign anyone out. The copy
 * in Preferences is deleted the moment it is read, never left behind.
 */
export function migratingSecureStorage(
  secure: SessionStorageAdapter = keychainStorage,
  legacy: SessionStorageAdapter = preferencesStorage,
): SessionStorageAdapter {
  return {
    async getItem(key) {
      const current = await secure.getItem(key);
      if (current !== null) return current;
      const previous = await legacy.getItem(key).catch(() => null);
      if (previous === null) return null;
      await secure.setItem(key, previous);
      await legacy.removeItem(key).catch(() => undefined);
      return previous;
    },
    setItem: (key, value) => secure.setItem(key, value),
    async removeItem(key) {
      await secure.removeItem(key);
      await legacy.removeItem(key).catch(() => undefined);
    },
  };
}

/**
 * The adapter the app should hand supabase-js: secure storage on a device,
 * Preferences (localStorage) in a browser, where no keychain exists and the
 * session was always going to sit in web storage anyway.
 */
export function sessionStorageAdapter(): SessionStorageAdapter {
  return Capacitor.isNativePlatform() ? migratingSecureStorage() : preferencesStorage;
}
