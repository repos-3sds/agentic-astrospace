import type { CapacitorSQLitePlugin } from '@capacitor-community/sqlite';

import { ResourceCacheEnvelope, ResourceCacheIdentity, resourceCacheKey } from './resource-cache';
import { NativeEncryptedResourceCachePersistence } from './resource-cache.persistence';

describe('NativeEncryptedResourceCachePersistence', () => {
  let sqlite: jasmine.SpyObj<CapacitorSQLitePlugin>;
  const identity: ResourceCacheIdentity = {
    userId: 'user-a',
    profileId: 'profile-a',
    resource: 'today',
    schemaVersion: 1,
  };
  const envelope: ResourceCacheEnvelope<{ headline: string }> = {
    identity,
    payload: { headline: 'Steady' },
    storedAt: 100,
    staleAt: 200,
    expiresAt: 300,
    source: 'network',
  };

  beforeEach(() => {
    sqlite = jasmine.createSpyObj<CapacitorSQLitePlugin>('CapacitorSQLite', [
      'isSecretStored', 'setEncryptionSecret', 'createConnection', 'open', 'execute', 'query', 'run',
      'isDatabaseEncrypted', 'closeConnection',
    ]);
    sqlite.isSecretStored.and.resolveTo({ result: false });
    sqlite.setEncryptionSecret.and.resolveTo();
    sqlite.createConnection.and.resolveTo();
    sqlite.open.and.resolveTo();
    sqlite.isDatabaseEncrypted.and.resolveTo({ result: true });
    sqlite.closeConnection.and.resolveTo();
    sqlite.execute.and.resolveTo({ changes: { changes: 0 } });
    sqlite.query.and.resolveTo({ values: [{ envelope: JSON.stringify(envelope) }] });
    sqlite.run.and.resolveTo({ changes: { changes: 1 } });
  });

  it('creates a device secret and opens only an encrypted connection', async () => {
    const persistence = new NativeEncryptedResourceCachePersistence(sqlite);

    const restored = await persistence.initialize();

    const secret = sqlite.setEncryptionSecret.calls.mostRecent().args[0].passphrase;
    expect(secret).toMatch(/^[a-f0-9]{64}$/);
    expect(sqlite.createConnection).toHaveBeenCalledWith(jasmine.objectContaining({
      encrypted: true,
      mode: 'secret',
      readonly: false,
    }));
    expect(restored).toEqual([envelope]);
  });

  it('writes owner-scoped envelopes and deletes by account without plaintext fallback', async () => {
    const persistence = new NativeEncryptedResourceCachePersistence(sqlite);
    await persistence.initialize();

    await persistence.put(resourceCacheKey(identity), envelope);
    await persistence.clearUser('user-a');

    expect(sqlite.run).toHaveBeenCalledWith(jasmine.objectContaining({
      statement: jasmine.stringMatching(/INSERT OR REPLACE/),
      values: jasmine.arrayContaining(['user-a', 'profile-a']),
    }));
    expect(sqlite.run).toHaveBeenCalledWith(jasmine.objectContaining({
      statement: 'DELETE FROM resource_cache WHERE user_id = ?',
      values: ['user-a'],
    }));
  });

  it('refuses writes before encrypted initialization succeeds', async () => {
    const persistence = new NativeEncryptedResourceCachePersistence(sqlite);

    await expectAsync(persistence.put(resourceCacheKey(identity), envelope)).toBeRejectedWithError(
      'Encrypted native cache is unavailable',
    );
  });

  it('rejects and closes a database that cannot prove encryption', async () => {
    sqlite.isDatabaseEncrypted.and.resolveTo({ result: false });
    const persistence = new NativeEncryptedResourceCachePersistence(sqlite);

    await expectAsync(persistence.initialize()).toBeRejectedWithError(
      'Native cache database did not open with SQLCipher encryption',
    );
    expect(sqlite.closeConnection).toHaveBeenCalledWith({ database: 'siddha_resources', readonly: false });
  });
});
