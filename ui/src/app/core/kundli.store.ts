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
    this.kundlis.set(await this.api.get<Kundli[]>('/kundlis'));
    this.loaded.set(true);
  }

  async create(payload: KundliPayload): Promise<Kundli> {
    const created = await this.api.post<Kundli>('/kundlis', payload);
    this.kundlis.update((list) => [...list, created]);
    return created;
  }

  async update(id: string, payload: Partial<KundliPayload>): Promise<Kundli> {
    const updated = await this.api.patch<Kundli>(`/kundlis/${id}`, payload);
    this.kundlis.update((list) => list.map((k) => (k.id === id ? updated : k)));
    this.vedic.invalidate(id);
    return updated;
  }

  async remove(id: string): Promise<void> {
    await this.api.delete(`/kundlis/${id}`);
    this.kundlis.update((list) => list.filter((k) => k.id !== id));
    this.vedic.invalidate(id);
    if (this.activeId() === id) this.activeId.set(null);
  }
}
