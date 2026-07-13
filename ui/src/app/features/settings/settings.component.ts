import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';
import { ButtonModule } from 'primeng/button';
import { Select } from 'primeng/select';
import { SelectButton } from 'primeng/selectbutton';

import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { KundliStore } from '../../core/kundli.store';
import { PanchangaCity } from '../../core/models';
import { PanchangaService } from '../../core/panchanga.service';
import { PreferencesService } from '../../core/preferences.service';
import { ThemeService } from '../../core/theme.service';
import { VedicService } from '../../core/vedic.service';
import { DefListComponent, DefRow } from '../../shared/def-list/def-list.component';
import { SectionCardComponent } from '../../shared/section-card/section-card.component';

@Component({
  selector: 'app-settings',
  imports: [
    RouterLink,
    FormsModule,
    LucideAngularModule,
    ButtonModule,
    Select,
    SelectButton,
    SectionCardComponent,
    DefListComponent,
  ],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss',
})
export class SettingsComponent {
  protected readonly store = inject(KundliStore);
  protected readonly theme = inject(ThemeService);
  protected readonly auth = inject(AuthService);
  protected readonly prefs = inject(PreferencesService);
  private api = inject(ApiService);
  private panchanga = inject(PanchangaService);
  private vedic = inject(VedicService);

  protected readonly migrationLoading = signal(false);
  protected readonly migrationMessage = signal<string | null>(null);
  protected readonly migrationError = signal<string | null>(null);
  protected readonly localKundlis = signal<number | null>(null);
  protected readonly cityOptions = signal<PanchangaCity[]>([]);
  protected readonly selectedPlace = signal<PanchangaCity | null>(null);
  protected readonly chartStyleOptions = [
    { label: 'South Indian', value: 'south' },
    { label: 'North Indian', value: 'north' },
  ];
  protected readonly ayanamshaOptions = [
    { label: 'Lahiri', value: 'lahiri' },
    { label: 'Raman', value: 'raman' },
    { label: 'KP', value: 'krishnamurti' },
  ];
  protected readonly nodeOptions = [
    { label: 'Mean node', value: 'mean' },
    { label: 'True node', value: 'true' },
  ];
  protected readonly timezoneOptions = [
    { label: 'Browser timezone', value: 'browser' },
    { label: 'Panchanga place', value: 'panchanga_place' },
  ];

  protected readonly accountRows = computed<DefRow[]>(() => [
    { label: 'Account', value: this.auth.email() },
    { label: 'Session', value: this.auth.enabled() ? 'Supabase Auth' : 'Local workspace' },
    { label: 'Saved kundlis', value: this.store.kundlis().length },
    { label: 'Theme', value: this.theme.dark() ? 'Dark' : 'Light' },
    { label: 'Chart style', value: this.prefs.chartStyle() === 'south' ? 'South Indian' : 'North Indian' },
    { label: 'Ayanamsha', value: this.prefs.ayanamsha() },
    { label: 'Node type', value: this.prefs.nodeType() },
  ]);

  protected readonly dataRows = computed<DefRow[]>(() => [
    { label: 'Storage', value: 'Backend database' },
    { label: 'AI provider', value: 'Anthropic via server' },
    { label: 'Chart engine', value: 'Vedic + Swiss Ephemeris' },
  ]);
  protected readonly preferenceRows = computed<DefRow[]>(() => [
    { label: 'Chart style', value: this.prefs.chartStyle() === 'south' ? 'South Indian' : 'North Indian' },
    { label: 'Ayanamsha', value: this.prefs.ayanamsha() },
    { label: 'Node type', value: this.prefs.nodeType() },
    { label: 'Timezone', value: this.prefs.effectiveTimezone() },
    { label: 'Panchanga place', value: this.prefs.panchangaPlace()?.label ?? 'Browser timezone place' },
  ]);

  constructor() {
    this.refreshMigrationStatus();
    this.panchanga
      .cities()
      .then((cities) => {
        this.cityOptions.set(cities);
        const saved = this.prefs.panchangaPlace();
        this.selectedPlace.set(
          saved ? cities.find((city) => city.city === saved.city && city.nation === saved.nation) ?? null : null,
        );
      })
      .catch(() => this.cityOptions.set([]));
  }

  protected setChartStyle(value: 'south' | 'north'): void {
    this.prefs.chartStyle.set(value);
  }

  protected setAyanamsha(value: 'lahiri' | 'raman' | 'krishnamurti'): void {
    this.prefs.ayanamsha.set(value);
    this.vedic.invalidateAll();
  }

  protected setNodeType(value: 'mean' | 'true'): void {
    this.prefs.nodeType.set(value);
    this.vedic.invalidateAll();
  }

  protected setTimezoneMode(value: 'browser' | 'panchanga_place'): void {
    this.prefs.timezoneMode.set(value);
  }

  protected setPanchangaPlace(place: PanchangaCity | null): void {
    this.selectedPlace.set(place);
    this.prefs.setPanchangaPlace(place);
  }

  protected resetPreferences(): void {
    this.prefs.reset();
    this.selectedPlace.set(null);
    this.vedic.invalidateAll();
  }

  protected async refreshMigrationStatus(): Promise<void> {
    if (!this.auth.enabled() || !this.auth.session()) return;
    try {
      const status = await this.api.get<{ local_kundlis: number; message: string }>(
        '/auth/migration/local',
      );
      this.localKundlis.set(status.local_kundlis);
      this.migrationMessage.set(status.message);
    } catch (e) {
      this.migrationError.set((e as Error).message);
    }
  }

  protected async claimLocalData(): Promise<void> {
    this.migrationLoading.set(true);
    this.migrationError.set(null);
    try {
      const result = await this.api.post<{ moved_kundlis: number; message: string }>(
        '/auth/migration/local/claim',
        {},
      );
      this.localKundlis.set(0);
      this.migrationMessage.set(result.message);
      await this.store.load();
    } catch (e) {
      this.migrationError.set((e as Error).message);
    } finally {
      this.migrationLoading.set(false);
    }
  }
}
