import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { KundliStore } from '../../../core/kundli.store';
import { DashaPayload, DashaPeriod, YoginiDashaPayload, YoginiDashaPeriod } from '../../../core/models';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';

interface Period {
  name: string;
  dates: string;
  active?: boolean;
  source?: DashaPeriod | YoginiDashaPeriod;
}

/** Life Periods / Dashas (Figma node 40:87), Antar level. */
@Component({
  selector: 'as-life-periods',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './life-periods.component.html',
  styleUrl: './life-periods.component.scss',
})
export class LifePeriodsComponent {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  protected readonly preferences = inject(PreferencesService);
  protected readonly data = signal<DashaPayload | null>(null);
  protected readonly yogini = signal<YoginiDashaPayload | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  readonly system = signal<'vimshottari' | 'yogini'>('vimshottari');
  readonly level = signal<'maha' | 'antar' | 'pratyantar' | 'sookshma' | 'prana'>('antar');

  readonly selectedMaha = signal<DashaPeriod | null>(null);
  readonly selectedAntar = signal<DashaPeriod | null>(null);

  // Sookshma/Prana are only computed along the *active* chain
  // (astrospace/core/vedic/dashas.py — a full 5-level tree for every branch
  // would be prohibitively large), so unlike Maha/Antar/Pratyantar these two
  // levels have no drill-into-an-arbitrary-period state of their own.
  readonly periods = computed(() => {
    if (this.system() === 'yogini') return (this.yogini()?.mahadashas ?? []).map((period) => this.toPeriod(period));
    if (this.level() === 'maha') return (this.data()?.mahadashas ?? []).map((period) => this.toPeriod(period));
    if (this.level() === 'pratyantar') return (this.selectedAntar()?.pratyantardashas ?? this.data()?.current.pratyantardashas ?? []).map((period) => this.toPeriod(period));
    if (this.level() === 'sookshma') return (this.data()?.current.sookshmadashas ?? []).map((period) => this.toPeriod(period));
    if (this.level() === 'prana') return (this.data()?.current.pranadashas ?? []).map((period) => this.toPeriod(period));
    return (this.selectedMaha()?.antardashas ?? this.data()?.current.mahadasha?.antardashas ?? []).map((period) => this.toPeriod(period));
  });
  readonly activePath = computed(() => {
    const current = this.data()?.current;
    return [current?.mahadasha?.lord, current?.antardasha?.lord, current?.pratyantardasha?.lord].filter(Boolean).join(' → ') || 'No active dasha';
  });
  readonly activeYogini = computed(() => this.yogini()?.current.mahadasha?.lord ?? this.yogini()?.mahadashas.find((period) => period.active)?.lord ?? 'No active Yogini');
  readonly mahaCrumb = computed(() => this.selectedMaha()?.lord ?? this.data()?.current.mahadasha?.lord ?? 'selected maha');
  readonly antarCrumb = computed(() => this.selectedAntar()?.lord ?? this.data()?.current.antardasha?.lord ?? 'selected antar');
  readonly pratyantarCrumb = computed(() => this.data()?.current.pratyantardasha?.lord ?? 'selected pratyantar');
  readonly sookshmaCrumb = computed(() => this.data()?.current.sookshmadasha?.lord ?? 'selected sookshma');

  // Sookshma/Prana are Practitioner-only — Balanced keeps the three-level
  // stack it already had; only Practitioner gets the full five.
  readonly levelTabs = computed(() =>
    this.preferences.experienceMode() === 'practitioner'
      ? (['maha', 'antar', 'pratyantar', 'sookshma', 'prana'] as const)
      : (['maha', 'antar', 'pratyantar'] as const),
  );

  constructor() {
    effect(() => {
      const activeId = this.kundlis.activeId();
      void this.load(activeId);
    });
  }

  protected chooseSystem(system: 'vimshottari' | 'yogini'): void {
    this.system.set(system);
    this.resetScroll();
  }

  protected chooseLevel(level: 'maha' | 'antar' | 'pratyantar' | 'sookshma' | 'prana'): void {
    this.system.set('vimshottari');
    this.level.set(level);
    this.resetScroll();
  }

  protected drill(period: Period): void {
    if (this.system() === 'yogini') return;
    const source = period.source as DashaPeriod | undefined;
    if (this.level() === 'maha' && source?.antardashas?.length) {
      this.selectedMaha.set(source);
      this.selectedAntar.set(source.antardashas.find((row) => row.active) ?? source.antardashas[0] ?? null);
      this.level.set('antar');
    } else if (this.level() === 'antar' && source?.pratyantardashas?.length) {
      this.selectedAntar.set(source);
      this.level.set('pratyantar');
    }
    this.resetScroll();
  }

  protected retry(): void {
    void this.load(this.kundlis.activeId());
  }

  private async load(expectedActiveId: string | null): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
      const activeId = this.kundlis.activeId();
      if (expectedActiveId && activeId !== expectedActiveId) return;
      if (!activeId) {
        this.data.set(null);
        this.yogini.set(null);
        return;
      }
      const [dashas, yogini] = await Promise.all([
        this.vedic.dashas(activeId),
        this.vedic.yoginiDashas(activeId).catch(() => null),
      ]);
      this.data.set(dashas);
      this.yogini.set(yogini);
      const maha = dashas.current.mahadasha ?? dashas.mahadashas[0] ?? null;
      const antar = dashas.current.antardasha ?? maha?.antardashas?.[0] ?? null;
      this.selectedMaha.set(maha);
      this.selectedAntar.set(antar);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  private toPeriod(period: DashaPeriod | YoginiDashaPeriod): Period {
    return {
      name: period.lord,
      dates: `${this.dateLabel(period.start)}–${this.dateLabel(period.end)}`,
      active: period.active,
      source: period,
    };
  }

  private dateLabel(value: string): string {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  }

  private resetScroll(): void {
    requestAnimationFrame(() => this.host.nativeElement.scrollIntoView({ block: 'start' }));
  }
}
