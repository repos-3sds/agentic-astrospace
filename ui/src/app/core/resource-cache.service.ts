import { Injectable, inject, signal } from '@angular/core';

import {
  CachedResource,
  ResourceCacheEnvelope,
  ResourceCacheIdentity,
  ResourceCacheMetadata,
  ResourceCachePolicy,
  ResourceCacheVersionExpectation,
  resourceCacheKey,
  resourceFreshness,
} from './resource-cache';
import { RESOURCE_CACHE_PERSISTENCE } from './resource-cache.persistence';

@Injectable({ providedIn: 'root' })
export class ResourceCacheService {
  private readonly persistence = inject(RESOURCE_CACHE_PERSISTENCE);
  private readonly memory = new Map<string, ResourceCacheEnvelope<unknown>>();
  private persistenceQueue = Promise.resolve();
  private initialized = false;
  readonly durability = signal<'initializing' | 'ready' | 'unavailable'>('initializing');

  async initialize(): Promise<void> {
    if (this.initialized) return;
    try {
      const envelopes = await this.persistence.initialize();
      const now = Date.now();
      for (const envelope of envelopes) {
        if (!this.validEnvelope(envelope)) continue;
        const key = resourceCacheKey(envelope.identity);
        if (resourceFreshness(envelope, now) === 'expired') {
          this.enqueue(() => this.persistence.deleteKey(key));
          continue;
        }
        this.memory.set(key, envelope);
      }
      this.initialized = true;
      this.durability.set('ready');
    } catch {
      // Native storage fails closed: memory remains usable for this process,
      // but private payloads are never redirected into WebView storage.
      this.initialized = true;
      this.durability.set('unavailable');
    }
  }

  async flush(): Promise<void> {
    await this.persistenceQueue;
  }

  get<T>(
    identity: ResourceCacheIdentity,
    now = Date.now(),
    expected: ResourceCacheVersionExpectation = {},
  ): CachedResource<T> | null {
    const key = resourceCacheKey(identity);
    const envelope = this.memory.get(key) as ResourceCacheEnvelope<T> | undefined;
    if (!envelope || resourceCacheKey(envelope.identity) !== key) return null;
    if (!this.matchesVersion(envelope, expected)) {
      this.deleteKey(key);
      return null;
    }
    const freshness = resourceFreshness(envelope, now);
    if (freshness === 'expired') {
      this.deleteKey(key);
      return null;
    }
    return {
      data: envelope.payload,
      freshness,
      storedAt: envelope.storedAt,
      expiresAt: envelope.expiresAt,
    };
  }

  set<T>(
    identity: ResourceCacheIdentity,
    payload: T,
    policy: ResourceCachePolicy,
    now = Date.now(),
    source: ResourceCacheEnvelope<T>['source'] = 'network',
    metadata: ResourceCacheMetadata = {},
  ): CachedResource<T> {
    if (policy.staleAfterMs < 0 || policy.expireAfterMs <= policy.staleAfterMs) {
      throw new Error('Cache policy requires expiry after the stale boundary');
    }
    const key = resourceCacheKey(identity);
    const authoritativeExpiry = metadata.validUntil ? Date.parse(metadata.validUntil) : Number.NaN;
    const expiresAt = Number.isFinite(authoritativeExpiry)
      ? Math.min(now + policy.expireAfterMs, authoritativeExpiry)
      : now + policy.expireAfterMs;
    if (expiresAt <= now) {
      this.deleteKey(key);
      return { data: payload, freshness: 'expired', storedAt: now, expiresAt };
    }
    const staleAt = Math.max(now, Math.min(now + policy.staleAfterMs, expiresAt - 1));
    const envelope: ResourceCacheEnvelope<T> = {
      identity,
      payload,
      storedAt: now,
      staleAt,
      expiresAt,
      engineVersion: metadata.engineVersion || undefined,
      datasetVersion: metadata.datasetVersion || undefined,
      source,
    };
    this.memory.set(key, envelope);
    this.enqueue(() => this.persistence.put(key, envelope));
    return { data: payload, freshness: 'fresh', storedAt: now, expiresAt: envelope.expiresAt };
  }

  deleteProfile(userId: string, profileId: string): void {
    this.deleteMemoryMatching((identity) => identity.userId === userId && identity.profileId === profileId);
    this.enqueue(() => this.persistence.deleteProfile(userId, profileId));
  }

  clearUser(userId: string): void {
    this.deleteMemoryMatching((identity) => identity.userId === userId);
    this.enqueue(() => this.persistence.clearUser(userId));
  }

  clearAll(): void {
    this.memory.clear();
    this.enqueue(() => this.persistence.clearAll());
  }

  discardLegacyUnscopedCaches(): void {
    const prefixes = ['astrospace.daily-guidance:', 'astrospace.calendar-intelligence:'];
    try {
      for (const key of Object.keys(localStorage)) {
        if (prefixes.some((prefix) => key.startsWith(prefix))) localStorage.removeItem(key);
      }
    } catch {
      // Best effort. Legacy entries are never read by this repository.
    }
  }

  private validEnvelope(value: ResourceCacheEnvelope<unknown>): boolean {
    return !!value
      && typeof value.identity === 'object'
      && typeof value.storedAt === 'number'
      && typeof value.staleAt === 'number'
      && typeof value.expiresAt === 'number'
      && value.staleAt >= value.storedAt
      && value.expiresAt > value.staleAt
      && (value.engineVersion === undefined || typeof value.engineVersion === 'string')
      && (value.datasetVersion === undefined || typeof value.datasetVersion === 'string')
      && Object.prototype.hasOwnProperty.call(value, 'payload');
  }

  private matchesVersion(
    envelope: ResourceCacheEnvelope<unknown>,
    expected: ResourceCacheVersionExpectation,
  ): boolean {
    // Missing metadata is tolerated for one rolling-deploy cycle. A present,
    // incompatible version is never surfaced as current.
    return (!expected.engineVersion || !envelope.engineVersion || envelope.engineVersion === expected.engineVersion)
      && (!expected.datasetVersion || !envelope.datasetVersion || envelope.datasetVersion === expected.datasetVersion);
  }

  private deleteMemoryMatching(predicate: (identity: ResourceCacheIdentity) => boolean): void {
    for (const [key, envelope] of this.memory) {
      if (predicate(envelope.identity)) this.memory.delete(key);
    }
  }

  private deleteKey(key: string): void {
    this.memory.delete(key);
    this.enqueue(() => this.persistence.deleteKey(key));
  }

  private enqueue(operation: () => Promise<void>): void {
    this.persistenceQueue = this.persistenceQueue.then(operation, operation).catch(() => undefined);
  }
}
