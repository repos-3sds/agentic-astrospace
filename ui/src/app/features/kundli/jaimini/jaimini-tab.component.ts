import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, computed, effect, inject, signal } from '@angular/core';
import { Skeleton } from 'primeng/skeleton';

import { KundliStore } from '../../../core/kundli.store';
import {
  ArudhaPada,
  JaiminiPayload,
  SpecialLagnasPayload,
  YoginiDashaPayload,
  YoginiDashaPeriod,
} from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { SectionCardComponent } from '../../../shared/section-card/section-card.component';

interface ArudhaGridCell {
  code: string;
  pada: ArudhaPada;
}

@Component({
  selector: 'app-jaimini-tab',
  imports: [DatePipe, DecimalPipe, Skeleton, SectionCardComponent],
  templateUrl: './jaimini-tab.component.html',
  styleUrl: './jaimini-tab.component.scss',
})
export class JaiminiTabComponent {
  private store = inject(KundliStore);
  private vedic = inject(VedicService);

  protected readonly kundli = this.store.active;
  protected readonly data = signal<JaiminiPayload | null>(null);
  protected readonly specialLagnas = signal<SpecialLagnasPayload | null>(null);
  protected readonly yogini = signal<YoginiDashaPayload | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly loading = computed(() => !this.data() && !this.error());
  protected readonly expandedMahadashaKey = signal<string | null>(null);

  protected readonly charaKarakas = computed(() => this.data()?.chara_karakas.ordered ?? []);

  protected readonly arudhaGrid = computed<ArudhaGridCell[]>(() => {
    const padas = this.data()?.arudha_padas?.padas ?? {};
    return Array.from({ length: 12 }, (_, i) => `A${i + 1}`)
      .filter((code) => !!padas[code])
      .map((code) => ({ code, pada: padas[code] }));
  });

  protected readonly specialLagnaRows = computed(() => {
    const s = this.specialLagnas();
    if (!s || s.error) return [];
    return [
      { label: 'Bhava Lagna', point: s.bhava_lagna },
      { label: 'Hora Lagna', point: s.hora_lagna },
      { label: 'Ghati Lagna', point: s.ghati_lagna },
      { label: 'Lagna', point: s.lagna },
    ].filter((row) => !!row.point);
  });

  protected readonly activeYoginiMahadasha = computed(
    () => this.yogini()?.current.mahadasha ?? null,
  );

  constructor() {
    effect(() => {
      const id = this.store.activeId();
      this.data.set(null);
      this.specialLagnas.set(null);
      this.yogini.set(null);
      this.error.set(null);
      this.expandedMahadashaKey.set(null);
      if (!id) return;
      this.vedic
        .jaimini(id)
        .then((payload) => this.data.set(payload))
        .catch((e) => this.error.set((e as Error).message));
      this.vedic
        .specialLagnas(id)
        .then((payload) => this.specialLagnas.set(payload))
        .catch(() => this.specialLagnas.set(null));
      this.vedic
        .yoginiDashas(id)
        .then((payload) => {
          this.yogini.set(payload);
          const active = payload.current.mahadasha;
          this.expandedMahadashaKey.set(active ? this.periodKey(active) : null);
        })
        .catch(() => this.yogini.set(null));
    });
  }

  protected toggleMahadasha(period: YoginiDashaPeriod): void {
    const key = this.periodKey(period);
    this.expandedMahadashaKey.set(this.expandedMahadashaKey() === key ? null : key);
  }

  protected periodKey(period: YoginiDashaPeriod): string {
    return `${period.yogini}:${period.start}:${period.end}`;
  }
}
