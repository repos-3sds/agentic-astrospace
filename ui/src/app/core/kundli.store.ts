import { Injectable, computed, effect, inject, signal, untracked } from '@angular/core';

import { ApiService } from './api.service';
import { AuthService } from './auth.service';
import { ConnectivityService } from './connectivity.service';
import { Kundli, KundliPayload } from './models';
import { PROFILES_CACHE_POLICY, ResourceCacheIdentity } from './resource-cache';
import { ResourceCacheService } from './resource-cache.service';
import { SessionTeardown } from './session-teardown';
import { VedicService } from './vedic.service';

/** Profile id used for the list itself, which belongs to no one profile. */
const PROFILE_LIST_SCOPE = 'profiles';

@Injectable({ providedIn: 'root' })
export class KundliStore {
  private api = inject(ApiService);
  private vedic = inject(VedicService);
  private auth = inject(AuthService);
  private cache = inject(ResourceCacheService);
  private connectivity = inject(ConnectivityService);

  readonly kundlis = signal<Kundli[]>([]);
  readonly loaded = signal(false);
  /** Why the last profile load failed, for the shell to show; null while fine. */
  readonly loadError = signal<string | null>(null);
  readonly activeId = signal<string | null>(null);
  readonly query = signal('');

  readonly active = computed(
    () => this.kundlis().find((k) => k.id === this.activeId()) ?? null,
  );
  /** The account holder's own profile. Greetings address this person, whose
   * chart is open notwithstanding: "Namaste, Bhaskar" to the owner reads as
   * the app mistaking who is holding the phone. */
  readonly owner = computed(() => {
    const profiles = this.kundlis();
    const self = profiles.find((k) => (k.relation ?? '').trim().toLowerCase() === 'self');
    if (self) return self;
    // Accounts from older builds can lack a "self" row (Hawk's own profile
    // was stored as "relative"); the first profile made is the holder's.
    const dated = profiles.filter((k) => k.created_at);
    return dated.length
      ? dated.reduce((first, k) => (k.created_at! < first.created_at! ? k : first))
      : profiles[0] ?? null;
  });
  private loadPromise: Promise<void> | null = null;
  private readonly activeStorageKey = 'astrospace.activeKundliId';
  /** The list on screen came from the device cache and the server has not confirmed it yet. */
  private needsRevalidation = false;
  /** Whose cached list is on screen, so reset() can drop exactly that entry. */
  private cacheOwner: string | null = null;

  constructor() {
    inject(SessionTeardown).register(() => {
      this.reset();
      try {
        localStorage.removeItem(this.activeStorageKey);
      } catch {
        // Storage unavailable; the in-memory selection is already gone.
      }
    });
    // Back online: confirm a cached list, or retry one that never loaded.
    effect(() => {
      if (this.connectivity.state() !== 'online') return;
      untracked(() => {
        if (this.needsRevalidation) void this.revalidate();
        else if (this.loadError() && !this.loaded()) void this.load().catch(() => undefined);
      });
    });
  }

  readonly filtered = computed(() => {
    const q = this.query().toLowerCase().trim();
    if (!q) return this.kundlis();
    return this.kundlis().filter(
      (k) =>
        k.name.toLowerCase().includes(q) ||
        (k.sun_sign ?? '').toLowerCase().includes(q) ||
        (k.relation ?? '').toLowerCase().includes(q),
    );
  });

  /* add/edit dialog state (dialog lives in the app shell) */
  readonly dialogOpen = signal(false);
  readonly editing = signal<Kundli | null>(null);

  openAdd(): void {
    this.editing.set(null);
    this.dialogOpen.set(true);
  }

  openEdit(kundli: Kundli): void {
    this.editing.set(kundli);
    this.dialogOpen.set(true);
  }

  closeDialog(): void {
    this.dialogOpen.set(false);
  }

  async load(): Promise<void> {
    if (this.loadPromise) return this.loadPromise;
    this.loadPromise = this.loadOnce();
    return this.loadPromise;
  }

  /** Drop every user-scoped value before another account can enter the shell. */
  reset(): void {
    this.vedic.clearConfiguredProfiles();
    if (this.cacheOwner) this.cache.deleteProfile(this.cacheOwner, PROFILE_LIST_SCOPE);
    this.cacheOwner = null;
    this.needsRevalidation = false;
    this.kundlis.set([]);
    this.activeId.set(null);
    this.loaded.set(false);
    this.loadError.set(null);
    this.loadPromise = null;
    this.query.set('');
    this.closeDialog();
  }

  /**
   * Stale-while-revalidate. A list cached on this device (SQLCipher on
   * native, localStorage on the web) is shown at once and confirmed in the
   * background; only a first load waits on the network. Until 2026-10-15 the
   * list was never cached, so an offline cold start showed "Your profiles
   * could not be loaded" over guidance that was sitting in the encrypted
   * cache the whole time.
   */
  private async loadOnce(): Promise<void> {
    this.loadError.set(null);
    const cached = this.readCachedProfiles();
    if (cached) {
      this.apply(cached);
      this.needsRevalidation = true;
      void this.revalidate();
      return;
    }
    try {
      await this.fetchProfiles();
    } catch (error) {
      this.loadPromise = null;
      this.loadError.set((error as Error)?.message || 'Your profiles could not be loaded.');
      throw error;
    }
  }

  private revalidating: Promise<void> | null = null;

  private revalidate(): Promise<void> {
    this.revalidating ??= this.fetchProfiles()
      .catch(() => {
        // The cached list stays on screen; the connectivity effect retries.
        this.needsRevalidation = true;
      })
      .finally(() => {
        this.revalidating = null;
      });
    return this.revalidating;
  }

  private async fetchProfiles(): Promise<void> {
    const owner = this.ownerId();
    const kundlis = await this.api.get<Kundli[]>('/kundlis');
    // A sign-out (or account switch) while the request was in flight: the
    // answer belongs to someone who is no longer here.
    if (owner !== this.ownerId()) return;
    this.needsRevalidation = false;
    this.apply(kundlis);
    this.persist();
  }

  private apply(kundlis: Kundli[]): void {
    this.kundlis.set(kundlis);
    for (const kundli of kundlis) this.vedic.configureProfile(kundli);
    const current = this.activeId();
    let storedId: string | null = null;
    try {
      storedId = localStorage.getItem(this.activeStorageKey);
    } catch {
      storedId = null;
    }
    const selected =
      kundlis.find((kundli) => kundli.id === current)
      ?? kundlis.find((kundli) => kundli.id === storedId)
      ?? kundlis[0]
      ?? null;
    this.setActive(selected?.id ?? null);
    this.loaded.set(true);
    this.loadError.set(null);
  }

  private ownerId(): string {
    // Auth disabled (dev, e2e) has no user; one local owner stands in.
    return this.auth.user()?.id ?? 'local';
  }

  private identity(owner = this.ownerId()): ResourceCacheIdentity {
    return { userId: owner, profileId: PROFILE_LIST_SCOPE, resource: 'profile-list', schemaVersion: 1 };
  }

  private readCachedProfiles(): Kundli[] | null {
    try {
      const owner = this.ownerId();
      const cached = this.cache.get<Kundli[]>(this.identity(owner));
      if (!cached || !Array.isArray(cached.data)) return null;
      this.cacheOwner = owner;
      return cached.data;
    } catch {
      return null;
    }
  }

  private persist(): void {
    try {
      const owner = this.ownerId();
      this.cache.set(this.identity(owner), this.kundlis(), PROFILES_CACHE_POLICY);
      this.cacheOwner = owner;
    } catch {
      // A cache write failing must not fail the load; the list is on screen.
    }
  }

  setActive(id: string | null): void {
    this.activeId.set(id);
    try {
      if (id) localStorage.setItem(this.activeStorageKey, id);
      else localStorage.removeItem(this.activeStorageKey);
    } catch {
      // Storage unavailable: the selection still holds for this session.
    }
  }

  /**
   * `activate: false` adds the profile without switching to it. Adding a
   * family member used to swap the whole app to them without a word, so the
   * Profiles screen adds quietly and lets the person choose; the first
   * profile is always made active, since there is nothing else to show.
   */
  async create(payload: KundliPayload, options: { activate?: boolean } = {}): Promise<Kundli> {
    const created = await this.api.post<Kundli>('/kundlis', payload);
    this.vedic.configureProfile(created);
    this.kundlis.update((list) => [...list, created]);
    if (options.activate !== false || !this.activeId()) this.setActive(created.id);
    this.persist();
    return created;
  }

  async update(id: string, payload: Partial<KundliPayload>): Promise<Kundli> {
    const updated = await this.api.patch<Kundli>(`/kundlis/${id}`, payload);
    this.kundlis.update((list) => list.map((k) => (k.id === id ? updated : k)));
    this.vedic.invalidate(id);
    this.vedic.configureProfile(updated);
    this.persist();
    return updated;
  }

  async remove(id: string): Promise<void> {
    await this.api.delete(`/kundlis/${id}`);
    this.kundlis.update((list) => list.filter((k) => k.id !== id));
    this.vedic.invalidate(id);
    this.vedic.removeConfiguredProfile(id);
    if (this.activeId() === id) this.setActive(this.kundlis()[0]?.id ?? null);
    this.persist();
  }
}
