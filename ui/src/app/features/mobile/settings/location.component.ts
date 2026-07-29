import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { PanchangaCity } from '../../../core/models';
import { PanchangaService } from '../../../core/panchanga.service';
import { PreferencesService } from '../../../core/preferences.service';

/** Which place the day's timings are computed for. */
export type TimingPlace = 'current' | 'selected';

/**
 * Settings — Location (Figma node 69:89).
 *
 * The footnote is the whole screen: the birth chart stays birth-based no matter
 * what is chosen here, and this only moves the daily panchang and windows.
 *
 * Without it the setting reads as "recompute my chart for where I am", which
 * would be wrong in a way people act on — a natal chart is fixed to the birth
 * moment and place, and nothing in an app should suggest it travels. What does
 * travel is sunrise, and with it Rahu Kalam, the tithi boundaries and every
 * muhurta window.
 */
@Component({
  selector: 'as-settings-location',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink],
  templateUrl: './location.component.html',
  styleUrl: './location.component.scss',
})
export class LocationComponent {
  private readonly preferences = inject(PreferencesService);
  private readonly panchanga = inject(PanchangaService);
  private searchRun = 0;

  readonly query = signal('');
  readonly suggestions = signal<PanchangaCity[]>([]);
  readonly searching = signal(false);
  readonly searchError = signal<string | null>(null);
  readonly selectedPlace = computed(() => this.preferences.panchangaPlace());
  readonly currentTimezone = computed(() => this.preferences.browserTimezone());
  readonly selectedLabel = computed(() => this.selectedPlace()?.label ?? 'Device timezone');
  readonly useSelectedCity = computed(() => this.preferences.timezoneMode() === 'panchanga_place' && !!this.selectedPlace());

  readonly places: { id: TimingPlace; icon: string; label: string; detail: string }[] = [
    {
      id: 'current',
      icon: 'loc-current',
      label: 'Current location',
      detail: 'Use this phone’s timezone for daily panchang, windows and Today.',
    },
    {
      id: 'selected',
      icon: 'loc-birth',
      label: 'Selected city',
      detail: 'Pin daily timing to a city when device location is not specific enough.',
    },
  ];

  readonly place = computed<TimingPlace>(() => this.useSelectedCity() ? 'selected' : 'current');

  constructor() {
    const saved = this.selectedPlace();
    if (saved) this.query.set(saved.label);
  }

  protected useCurrentLocation(): void {
    this.preferences.timezoneMode.set('browser');
    this.preferences.setPanchangaPlace(null);
    this.query.set('');
    this.suggestions.set([]);
    this.searchError.set(null);
  }

  protected choosePlace(mode: TimingPlace): void {
    if (mode === 'current') {
      this.useCurrentLocation();
      return;
    }
    const saved = this.selectedPlace();
    if (saved) {
      this.preferences.timezoneMode.set('panchanga_place');
      this.query.set(saved.label);
    }
  }

  protected onQuery(value: string): void {
    this.query.set(value);
    void this.searchCities(value);
  }

  protected selectCity(city: PanchangaCity): void {
    this.preferences.setPanchangaPlace(city);
    this.preferences.timezoneMode.set('panchanga_place');
    this.query.set(city.label);
    this.suggestions.set([]);
    this.searchError.set(null);
  }

  private async searchCities(value: string): Promise<void> {
    const q = value.trim();
    const run = ++this.searchRun;
    if (q.length < 2) {
      this.suggestions.set([]);
      this.searchError.set(null);
      return;
    }
    this.searching.set(true);
    this.searchError.set(null);
    try {
      const cities = await this.panchanga.cities(q);
      if (run === this.searchRun) this.suggestions.set(cities.slice(0, 8));
    } catch (error) {
      if (run === this.searchRun) {
        this.suggestions.set([]);
        this.searchError.set((error as Error).message);
      }
    } finally {
      if (run === this.searchRun) this.searching.set(false);
    }
  }
}
