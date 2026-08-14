import { Injectable, computed, inject, signal } from '@angular/core';

import { ApiService } from './api.service';
import { Kundli, KundliPayload } from './models';
import { VedicService } from './vedic.service';

@Injectable({ providedIn: 'root' })
export class KundliStore {
  private api = inject(ApiService);
  private vedic = inject(VedicService);

  readonly kundlis = signal<Kundli[]>([]);
  readonly loaded = signal(false);
  readonly activeId = signal<string | null>(null);
  readonly query = signal('');

  readonly active = computed(
    () => this.kundlis().find((k) => k.id === this.activeId()) ?? null,
  );
  private loadPromise: Promise<void> | null = null;
  private readonly activeStorageKey = 'astrospace.activeKundliId';

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
    this.kundlis.set([]);
    this.activeId.set(null);
    this.loaded.set(false);
    this.loadPromise = null;
    this.query.set('');
    this.closeDialog();
  }

  private async loadOnce(): Promise<void> {
    try {
      const kundlis = await this.api.get<Kundli[]>('/kundlis');
      this.kundlis.set(kundlis);
      for (const kundli of kundlis) this.vedic.configureProfile(kundli);
      const storedId = localStorage.getItem(this.activeStorageKey);
      const selected = kundlis.find((kundli) => kundli.id === storedId) ?? kundlis[0] ?? null;
      this.setActive(selected?.id ?? null);
      this.loaded.set(true);
    } catch (error) {
      this.loadPromise = null;
      throw error;
    }
  }

  setActive(id: string | null): void {
    this.activeId.set(id);
    if (id) localStorage.setItem(this.activeStorageKey, id);
    else localStorage.removeItem(this.activeStorageKey);
  }

  async create(payload: KundliPayload): Promise<Kundli> {
    const created = await this.api.post<Kundli>('/kundlis', payload);
    this.vedic.configureProfile(created);
    this.kundlis.update((list) => [...list, created]);
    this.setActive(created.id);
    return created;
  }

  async update(id: string, payload: Partial<KundliPayload>): Promise<Kundli> {
    const updated = await this.api.patch<Kundli>(`/kundlis/${id}`, payload);
    this.kundlis.update((list) => list.map((k) => (k.id === id ? updated : k)));
    this.vedic.invalidate(id);
    this.vedic.configureProfile(updated);
    return updated;
  }

  async remove(id: string): Promise<void> {
    await this.api.delete(`/kundlis/${id}`);
    this.kundlis.update((list) => list.filter((k) => k.id !== id));
    this.vedic.invalidate(id);
    this.vedic.removeConfiguredProfile(id);
    if (this.activeId() === id) this.setActive(this.kundlis()[0]?.id ?? null);
  }
}
