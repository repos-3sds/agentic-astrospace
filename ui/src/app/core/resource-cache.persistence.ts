import { InjectionToken } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import { CapacitorSQLite } from '@capacitor-community/sqlite';
import type { CapacitorSQLitePlugin } from '@capacitor-community/sqlite';

import { ResourceCacheEnvelope, ResourceCacheIdentity, resourceCacheKey } from './resource-cache';

const STORAGE_PREFIX = 'siddha.resource-cache:v1:';
const DATABASE = 'siddha_resources';

export interface ResourceCachePersistence {
  readonly native: boolean;
  initialize(): Promise<ResourceCacheEnvelope<unknown>[]>;
  put(key: string, envelope: ResourceCacheEnvelope<unknown>): Promise<void>;
  deleteKey(key: string): Promise<void>;
  deleteProfile(userId: string, profileId: string): Promise<void>;
  clearUser(userId: string): Promise<void>;
  clearAll(): Promise<void>;
}

export class WebResourceCachePersistence implements ResourceCachePersistence {
  readonly native = false;

  async initialize(): Promise<ResourceCacheEnvelope<unknown>[]> {
    const envelopes: ResourceCacheEnvelope<unknown>[] = [];
    try {
      for (const key of Object.keys(localStorage)) {
        if (!key.startsWith(STORAGE_PREFIX)) continue;
        try {
          const raw = localStorage.getItem(key);
          if (raw) envelopes.push(JSON.parse(raw) as ResourceCacheEnvelope<unknown>);
        } catch {
          localStorage.removeItem(key);
        }
      }
    } catch {
      // The cache service validates every returned envelope.
    }
    return envelopes;
  }

  async put(key: string, envelope: ResourceCacheEnvelope<unknown>): Promise<void> {
    localStorage.setItem(`${STORAGE_PREFIX}${key}`, JSON.stringify(envelope));
  }

  async deleteKey(key: string): Promise<void> {
    localStorage.removeItem(`${STORAGE_PREFIX}${key}`);
  }

  async deleteProfile(userId: string, profileId: string): Promise<void> {
    this.deleteMatching((identity) => identity.userId === userId && identity.profileId === profileId);
  }

  async clearUser(userId: string): Promise<void> {
    this.deleteMatching((identity) => identity.userId === userId);
  }

  async clearAll(): Promise<void> {
    this.deleteMatching(() => true);
  }

  private deleteMatching(predicate: (identity: ResourceCacheIdentity) => boolean): void {
    for (const key of Object.keys(localStorage)) {
      if (!key.startsWith(STORAGE_PREFIX)) continue;
      try {
        const value = JSON.parse(localStorage.getItem(key) ?? '') as ResourceCacheEnvelope<unknown>;
        if (predicate(value.identity)) localStorage.removeItem(key);
      } catch {
        localStorage.removeItem(key);
      }
    }
  }
}

export class NativeEncryptedResourceCachePersistence implements ResourceCachePersistence {
  readonly native = true;
  private ready = false;

  constructor(private readonly sqlite: CapacitorSQLitePlugin = CapacitorSQLite) {}

  async initialize(): Promise<ResourceCacheEnvelope<unknown>[]> {
    const secret = await this.sqlite.isSecretStored();
    if (!secret.result) {
      await this.sqlite.setEncryptionSecret({ passphrase: randomSecret() });
    }
    await this.sqlite.createConnection({
      database: DATABASE,
      version: 1,
      encrypted: true,
      mode: 'secret',
      readonly: false,
    });
    await this.sqlite.open({ database: DATABASE });
    const encrypted = await this.sqlite.isDatabaseEncrypted({ database: DATABASE });
    if (!encrypted.result) {
      await this.sqlite.closeConnection({ database: DATABASE, readonly: false });
      throw new Error('Native cache database did not open with SQLCipher encryption');
    }
    await this.sqlite.execute({
      database: DATABASE,
      statements: `
        CREATE TABLE IF NOT EXISTS resource_cache (
          cache_key TEXT PRIMARY KEY NOT NULL,
          user_id TEXT NOT NULL,
          profile_id TEXT NOT NULL,
          expires_at INTEGER NOT NULL,
          envelope TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_resource_cache_owner
          ON resource_cache(user_id, profile_id);
      `,
      transaction: true,
    });
    this.ready = true;
    const rows = await this.sqlite.query({
      database: DATABASE,
      statement: 'SELECT envelope FROM resource_cache',
      values: [],
    });
    return (rows.values ?? []).flatMap((row) => {
      try {
        return [JSON.parse(String(row['envelope'])) as ResourceCacheEnvelope<unknown>];
      } catch {
        return [];
      }
    });
  }

  async put(key: string, envelope: ResourceCacheEnvelope<unknown>): Promise<void> {
    this.assertReady();
    await this.sqlite.run({
      database: DATABASE,
      statement: `INSERT OR REPLACE INTO resource_cache
        (cache_key, user_id, profile_id, expires_at, envelope) VALUES (?, ?, ?, ?, ?)`,
      values: [key, envelope.identity.userId, envelope.identity.profileId, envelope.expiresAt, JSON.stringify(envelope)],
      transaction: true,
    });
  }

  async deleteKey(key: string): Promise<void> {
    await this.runDelete('DELETE FROM resource_cache WHERE cache_key = ?', [key]);
  }

  async deleteProfile(userId: string, profileId: string): Promise<void> {
    await this.runDelete('DELETE FROM resource_cache WHERE user_id = ? AND profile_id = ?', [userId, profileId]);
  }

  async clearUser(userId: string): Promise<void> {
    await this.runDelete('DELETE FROM resource_cache WHERE user_id = ?', [userId]);
  }

  async clearAll(): Promise<void> {
    await this.runDelete('DELETE FROM resource_cache', []);
  }

  private async runDelete(statement: string, values: any[]): Promise<void> {
    this.assertReady();
    await this.sqlite.run({ database: DATABASE, statement, values, transaction: true });
  }

  private assertReady(): void {
    if (!this.ready) throw new Error('Encrypted native cache is unavailable');
  }
}

export const RESOURCE_CACHE_PERSISTENCE = new InjectionToken<ResourceCachePersistence>(
  'RESOURCE_CACHE_PERSISTENCE',
  {
    providedIn: 'root',
    factory: () => Capacitor.isNativePlatform()
      ? new NativeEncryptedResourceCachePersistence()
      : new WebResourceCachePersistence(),
  },
);

function randomSecret(): string {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (value) => value.toString(16).padStart(2, '0')).join('');
}
