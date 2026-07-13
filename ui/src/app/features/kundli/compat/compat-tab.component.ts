import { Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Select } from 'primeng/select';
import { Skeleton } from 'primeng/skeleton';

import { ApiService } from '../../../core/api.service';
import { KundliStore } from '../../../core/kundli.store';
import { CompatibilityPayload, Kundli, VedicAll } from '../../../core/models';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { KundliChartComponent } from '../../../shared/kundli-chart/kundli-chart.component';
import { MarkdownPipe } from '../../../shared/markdown.pipe';
import { SectionCardComponent } from '../../../shared/section-card/section-card.component';

interface CompatDetail {
  name: string;
  relation: string;
  birth: string;
  place: string;
  sun: string;
  moon: string;
  lagna: string;
  nakshatra: string;
  varna: string;
  vashya: string;
  yoni: string;
  gana: string;
  nadi: string;
}

@Component({
  selector: 'app-compat-tab',
  imports: [FormsModule, Select, Skeleton, MarkdownPipe, SectionCardComponent, KundliChartComponent],
  templateUrl: './compat-tab.component.html',
  styleUrl: './compat-tab.component.scss',
})
export class CompatTabComponent {
  private store = inject(KundliStore);
  private api = inject(ApiService);
  private vedic = inject(VedicService);
  protected readonly prefs = inject(PreferencesService);

  protected readonly kundli = this.store.active;
  protected readonly partnerId = signal<string | null>(null);
  protected readonly activeVedic = signal<VedicAll | null>(null);
  protected readonly partnerVedic = signal<VedicAll | null>(null);
  protected readonly compatibility = signal<CompatibilityPayload | null>(null);
  protected readonly chartError = signal<string | null>(null);

  protected readonly others = computed(() =>
    this.store
      .kundlis()
      .filter((k) => k.id !== this.store.activeId())
      .map((k) => ({ label: `${k.name} (${k.sun_sign || 'Unknown'})`, value: k.id })),
  );

  protected readonly partner = computed(() => this.store.kundlis().find((k) => k.id === this.partnerId()) ?? null);
  protected readonly details = computed(() => {
    const a = this.kundli();
    const b = this.partner();
    const av = this.activeVedic();
    const bv = this.partnerVedic();
    if (!a || !b) return null;
    return {
      a: this.detail(a, av),
      b: this.detail(b, bv),
    };
  });
  protected readonly score = computed(() => this.compatibility());

  protected readonly result = signal<string | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly loading = signal(false);
  protected readonly chartLoading = computed(() =>
    !!this.partnerId() && (!this.activeVedic() || !this.partnerVedic() || !this.compatibility()) && !this.chartError(),
  );

  constructor() {
    effect(() => {
      const id = this.store.activeId();
      this.activeVedic.set(null);
      this.chartError.set(null);
      if (!id) return;
      this.vedic
        .all(id)
        .then((data) => this.activeVedic.set(data))
        .catch((e) => this.chartError.set((e as Error).message));
    });
  }

  protected async selectPartner(partnerId: string | null): Promise<void> {
    this.partnerId.set(partnerId);
    this.partnerVedic.set(null);
    this.compatibility.set(null);
    this.result.set(null);
    this.error.set(null);
    this.chartError.set(null);
    if (!partnerId) return;

    try {
      const activeId = this.store.activeId();
      if (!activeId) return;
      const [partnerData, score] = await Promise.all([
        this.vedic.all(partnerId),
        this.vedic.compatibility(activeId, partnerId),
      ]);
      this.partnerVedic.set(partnerData);
      this.compatibility.set(score);
    } catch (e) {
      this.chartError.set((e as Error).message);
    }
  }

  protected async runAi(): Promise<void> {
    const a = this.store.active();
    const b = this.partner();
    if (!a || !b) return;

    const person = (k: Kundli) => ({
      name: k.name,
      year: k.birth_year,
      month: k.birth_month,
      day: k.birth_day,
      hour: k.birth_hour,
      minute: k.birth_minute,
      city: k.birth_city,
      nation: k.birth_nation,
    });

    this.loading.set(true);
    this.error.set(null);
    this.result.set(null);
    try {
      const data = await this.api.post<Record<string, string>>('/compatibility', {
        person1: person(a),
        person2: person(b),
      });
      this.result.set(
        data['compatibility'] || data['analysis'] || data['content'] || JSON.stringify(data),
      );
    } catch (e) {
      this.error.set((e as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  private detail(k: Kundli, vedic: VedicAll | null): CompatDetail {
    return {
      name: k.name,
      relation: k.relation || 'Profile',
      birth: `${k.birth_day}/${k.birth_month}/${k.birth_year} · ${String(k.birth_hour).padStart(2, '0')}:${String(k.birth_minute).padStart(2, '0')}`,
      place: [k.birth_city, k.birth_nation].filter(Boolean).join(', '),
      sun: vedic?.planets['Sun']?.sign ?? k.sun_sign ?? '—',
      moon: vedic?.planets['Moon']?.sign ?? k.moon_sign ?? '—',
      lagna: vedic?.vargas['D1']?.lagna.sign ?? k.ascendant ?? '—',
      nakshatra: vedic?.planets['Moon']?.nakshatra ?? '—',
      varna: this.av(vedic, 'varna'),
      vashya: this.av(vedic, 'vashya'),
      yoni: this.av(vedic, 'yoni'),
      gana: this.av(vedic, 'gana'),
      nadi: this.av(vedic, 'nadi'),
    };
  }

  private av(vedic: VedicAll | null, key: string): string {
    const value = vedic?.avkahada?.[key];
    return value === null || value === undefined || value === '' ? '—' : String(value);
  }
}
