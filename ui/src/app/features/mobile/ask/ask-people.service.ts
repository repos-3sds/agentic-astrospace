import { Injectable, computed, inject, signal } from '@angular/core';
import { KundliStore } from '../../../core/kundli.store';

/** Others besides the open profile; five people in all (server: context/people.py). */
export const MAX_ASK_WITH = 4;

/**
 * Who else a question is about (Hawk, 2026-10-29): a couple buying a house,
 * friends starting a venture, the family moving. The reader picks them under
 * "+" and Ask reads every chart together for the shared purpose. Names and
 * relationships typed in the question are matched on the server as well, so
 * this is a way to be sure, not the only way in.
 *
 * Tied to the open profile: switching profile starts the list again, since
 * "Lakshmi and me" means something else from Arjun's chart.
 */
@Injectable({ providedIn: 'root' })
export class AskPeopleService {
  private readonly kundlis = inject(KundliStore);
  private readonly picked = signal<{ owner: string | null; ids: string[] }>({ owner: null, ids: [] });

  /** Profiles that may join the open one. */
  readonly options = computed(() => {
    const active = this.kundlis.activeId();
    return this.kundlis.kundlis().filter((k) => k.id !== active);
  });

  /** The picked profiles that still exist, for the open profile only. */
  readonly ids = computed(() => {
    const { owner, ids } = this.picked();
    if (owner !== this.kundlis.activeId()) return [];
    const allowed = new Set(this.options().map((k) => k.id));
    return ids.filter((id) => allowed.has(id));
  });

  readonly names = computed(() =>
    this.ids().map((id) => this.kundlis.kundlis().find((k) => k.id === id)?.name.split(' ')[0] ?? '').filter(Boolean));

  readonly full = computed(() => this.ids().length >= MAX_ASK_WITH);

  toggle(id: string): void {
    const current = this.ids();
    const next = current.includes(id) ? current.filter((i) => i !== id)
      : current.length < MAX_ASK_WITH ? [...current, id] : current;
    this.picked.set({ owner: this.kundlis.activeId(), ids: next });
  }

  clear(): void {
    this.picked.set({ owner: null, ids: [] });
  }
}
