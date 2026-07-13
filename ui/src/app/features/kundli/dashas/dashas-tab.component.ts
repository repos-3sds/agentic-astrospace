import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, computed, effect, inject, signal } from '@angular/core';
import { Skeleton } from 'primeng/skeleton';

import { KundliStore } from '../../../core/kundli.store';
import { DashaPayload, DashaPeriod, TransitContextPayload } from '../../../core/models';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { KundliChartComponent } from '../../../shared/kundli-chart/kundli-chart.component';
import { SectionCardComponent } from '../../../shared/section-card/section-card.component';

@Component({
  selector: 'app-dashas-tab',
  imports: [DatePipe, DecimalPipe, Skeleton, SectionCardComponent, KundliChartComponent],
  templateUrl: './dashas-tab.component.html',
  styleUrl: './dashas-tab.component.scss',
})
export class DashasTabComponent {
  private store = inject(KundliStore);
  private vedic = inject(VedicService);
  protected readonly prefs = inject(PreferencesService);

  protected readonly data = signal<DashaPayload | null>(null);
  protected readonly transit = signal<TransitContextPayload | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly selectedMahadashaKey = signal<string | null>(null);
  protected readonly selectedAntardashaKey = signal<string | null>(null);
  protected readonly detailMode = signal<'summary' | 'natal' | 'transit' | 'timeline'>('summary');
  protected readonly detailModes = [
    { label: 'Summary', value: 'summary' as const },
    { label: 'Natal', value: 'natal' as const },
    { label: 'Transit', value: 'transit' as const },
    { label: 'Timeline', value: 'timeline' as const },
  ];
  protected readonly loading = computed(() => !this.data() && !this.error());

  protected readonly activeMahadasha = computed(() => this.data()?.current.mahadasha ?? null);
  protected readonly activeAntardasha = computed(() => this.data()?.current.antardasha ?? null);
  protected readonly activePratyantardasha = computed(
    () => this.data()?.current.pratyantardasha ?? null,
  );

  protected readonly activeAntardashas = computed<DashaPeriod[]>(
    () => this.activeMahadasha()?.antardashas ?? [],
  );

  protected readonly selectedMahadasha = computed<DashaPeriod | null>(() => {
    const periods = this.data()?.mahadashas ?? [];
    return (
      periods.find((p) => this.periodKey(p) === this.selectedMahadashaKey()) ??
      this.activeMahadasha() ??
      periods[0] ??
      null
    );
  });

  protected readonly selectedAntardashas = computed<DashaPeriod[]>(
    () => this.selectedMahadasha()?.antardashas ?? [],
  );

  protected readonly selectedAntardasha = computed<DashaPeriod | null>(() => {
    const periods = this.selectedAntardashas();
    return (
      periods.find((p) => this.periodKey(p) === this.selectedAntardashaKey()) ??
      (this.selectedMahadasha()?.active ? this.activeAntardasha() : null) ??
      periods[0] ??
      null
    );
  });

  protected readonly selectedPratyantardashas = computed<DashaPeriod[]>(() => {
    const p = this.selectedAntardasha();
    return p?.pratyantardashas ?? [];
  });

  protected readonly selectedLord = computed(
    () => this.activeSelection().lord ?? this.selectedAntardasha()?.lord ?? this.selectedMahadasha()?.lord ?? null,
  );

  protected readonly activeSelection = computed(() => {
    const pd = this.activePratyantardasha();
    const ad = this.selectedAntardasha();
    const md = this.selectedMahadasha();
    return {
      lord: pd?.lord ?? ad?.lord ?? md?.lord ?? null,
      period: pd ?? ad ?? md ?? null,
      path: [md?.lord, ad?.lord, pd?.lord].filter(Boolean).join(' / '),
    };
  });

  protected readonly selectedTransit = computed(() => {
    const lord = this.selectedLord();
    return lord ? this.transit()?.gochara[lord] ?? null : null;
  });

  protected readonly selectedNatalRashi = computed(() => {
    const lord = this.selectedLord();
    return lord ? this.transit()?.natal.rashi.planets[lord] ?? null : null;
  });

  protected readonly selectedNatalNavamsha = computed(() => {
    const lord = this.selectedLord();
    return lord ? this.transit()?.natal.navamsha.planets[lord] ?? null : null;
  });

  constructor() {
    effect(() => {
      const id = this.store.activeId();
      this.data.set(null);
      this.transit.set(null);
      this.error.set(null);
      this.selectedMahadashaKey.set(null);
      this.selectedAntardashaKey.set(null);
      if (!id) return;
      this.vedic
        .dashas(id)
        .then((d) => {
          this.data.set(d);
          const md = d.current.mahadasha ?? d.mahadashas[0] ?? null;
          const ad = d.current.antardasha ?? md?.antardashas?.[0] ?? null;
          this.selectedMahadashaKey.set(md ? this.periodKey(md) : null);
          this.selectedAntardashaKey.set(ad ? this.periodKey(ad) : null);
        })
        .catch((e) => this.error.set((e as Error).message));
      this.vedic
        .transitContext(id)
        .then((t) => this.transit.set(t))
        .catch((e) => this.error.set((e as Error).message));
    });
  }

  protected selectMahadasha(period: DashaPeriod): void {
    this.selectedMahadashaKey.set(this.periodKey(period));
    const ad = period.active ? this.activeAntardasha() : period.antardashas?.[0];
    this.selectedAntardashaKey.set(ad ? this.periodKey(ad) : null);
  }

  protected selectAntardasha(period: DashaPeriod): void {
    this.selectedAntardashaKey.set(this.periodKey(period));
  }

  protected periodKey(period: DashaPeriod): string {
    return `${period.lord}:${period.start}:${period.end}`;
  }

}
