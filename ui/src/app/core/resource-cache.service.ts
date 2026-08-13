import { Injectable } from '@angular/core';

import {
  CachedResource,
  ResourceCacheEnvelope,
  ResourceCacheIdentity,
  ResourceCachePolicy,
  resourceCacheKey,
  resourceFreshness,
} from './resource-cache';

const STORAGE_PREFIX = 'siddha.resource-cache:v1:';

@Injectable({ providedIn: 'root' })
export class ResourceCacheService {
  private readonly memory = new Map<string, ResourceCacheEnvelope<unknown>>();

  get<T>(identity: ResourceCacheIdentity, now = Date.now()): CachedResource<T> | null {
    const key = resourceCacheKey(identity);
    let envelope = this.memory.get(key) as ResourceCacheEnvelope<T> | undefined;
    if (!envelope) {
      envelope = this.read<T>(key);
      if (envelope) this.memory.set(key, envelope);
    }
    if (!envelope || resourceCacheKey(envelope.identity) !== key) return null;
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
  ): CachedResource<T> {
    if (policy.staleAfterMs < 0 || policy.expireAfterMs <= policy.staleAfterMs) {
      throw new Error('Cache policy requires expiry after the stale boundary');
    }
    const key = resourceCacheKey(identity);
    const envelope: ResourceCacheEnvelope<T> = {
      identity,
      payload,
      storedAt: now,
      staleAt: now + policy.staleAfterMs,
      expiresAt: now + policy.expireAfterMs,
      source,
    };
    this.memory.set(key, envelope);
    try {
      localStorage.setItem(`${STORAGE_PREFIX}${key}`, JSON.stringify(envelope));
    } catch {
      // A full/unavailable WebView store must not discard the usable memory copy.
    }
    return { data: payload, freshness: 'fresh', storedAt: now, expiresAt: envelope.expiresAt };
  }

  deleteProfile(userId: string, profileId: string): void {
    this.deleteMatching((identity) => identity.userId === userId && identity.profileId === profileId);
  }

  clearUser(userId: string): void {
    this.deleteMatching((identity) => identity.userId === userId);
  }

  clearAll(): void {
    this.memory.clear();
    this.deleteStoredWhere(() => true);
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

  private read<T>(key: string): ResourceCacheEnvelope<T> | undefined {
    try {
      const raw = localStorage.getItem(`${STORAGE_PREFIX}${key}`);
      if (!raw) return undefined;
      const envelope = JSON.parse(raw) as ResourceCacheEnvelope<T>;
      if (!this.validEnvelope(envelope)) throw new Error('Invalid cache envelope');
      return envelope;
    } catch {
      try {
        localStorage.removeItem(`${STORAGE_PREFIX}${key}`);
      } catch {
        // Storage may be unavailable; the malformed value remains unreachable.
      }
      return undefined;
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
      && Object.prototype.hasOwnProperty.call(value, 'payload');
  }

  private deleteMatching(predicate: (identity: ResourceCacheIdentity) => boolean): void {
    for (const [key, envelope] of this.memory) {
      if (predicate(envelope.identity)) this.memory.delete(key);
    }
    this.deleteStoredWhere(predicate);
  }

  private deleteStoredWhere(predicate: (identity: ResourceCacheIdentity) => boolean): void {
    try {
      for (const storageKey of Object.keys(localStorage)) {
        if (!storageKey.startsWith(STORAGE_PREFIX)) continue;
        try {
          const envelope = JSON.parse(localStorage.getItem(storageKey) ?? '') as ResourceCacheEnvelope<unknown>;
          if (this.validEnvelope(envelope) && predicate(envelope.identity)) localStorage.removeItem(storageKey);
        } catch {
          localStorage.removeItem(storageKey);
        }
      }
    } catch {
      // Memory cleanup still provides isolation for the running process.
    }
  }

  private deleteKey(key: string): void {
    this.memory.delete(key);
    try {
      localStorage.removeItem(`${STORAGE_PREFIX}${key}`);
    } catch {
      // Ignore unavailable storage; memory no longer exposes the value.
    }
  }
}
