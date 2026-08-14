import { ChangeDetectionStrategy, Component, EventEmitter, Input, OnDestroy, Output, inject, signal } from '@angular/core';

import { PanchangaCity } from '../../../core/models';
import { PanchangaService } from '../../../core/panchanga.service';

@Component({
  selector: 'as-birth-place-field',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <label for="profile-birth-place">PLACE OF BIRTH</label>
    <div class="place-input" [class.active]="query().length > 0 && !selected()">
      <img src="mobile/pin.svg" alt="" aria-hidden="true" />
      <input id="profile-birth-place" type="search" autocomplete="off" placeholder="Search city or town"
        [value]="query()" [attr.aria-expanded]="matches().length > 0" aria-controls="profile-place-results"
        (input)="search($any($event.target).value)" />
    </div>
    @if (loading()) { <p class="status" role="status">Searching places...</p> }
    @if (matches().length > 0) {
      <ul id="profile-place-results" role="listbox" aria-label="Matching birth places">
        @for (place of matches(); track place.label + place.lat + place.lng) {
          <li><button type="button" role="option" (click)="choose(place)">
            <img src="mobile/pin.svg" alt="" aria-hidden="true" />
            <span><b>{{ place.city }}</b><small>{{ place.label || (place.nation + ' · ' + place.timezone) }}</small></span>
          </button></li>
        }
      </ul>
    }
    @if (searchError()) { <p class="error" role="alert">{{ searchError() }}</p> }
  `,
  styleUrl: './birth-place-field.component.scss',
})
export class BirthPlaceFieldComponent implements OnDestroy {
  private readonly panchanga = inject(PanchangaService);
  private searchSequence = 0;
  private searchTimer: ReturnType<typeof setTimeout> | null = null;
  readonly query = signal('');
  readonly selected = signal<PanchangaCity | null>(null);
  readonly matches = signal<PanchangaCity[]>([]);
  readonly loading = signal(false);
  readonly searchError = signal<string | null>(null);
  @Output() readonly placeChange = new EventEmitter<PanchangaCity | null>();

  @Input() set initialPlace(place: Pick<PanchangaCity, 'city' | 'nation'> | null) {
    if (!place?.city || this.query()) return;
    this.query.set(place.city);
    this.selected.set({ ...place, label: place.city } as PanchangaCity);
  }

  search(value: string): void {
    this.query.set(value);
    this.selected.set(null);
    this.placeChange.emit(null);
    this.searchError.set(null);
    const query = value.trim();
    const sequence = ++this.searchSequence;
    if (this.searchTimer) clearTimeout(this.searchTimer);
    if (query.length < 2) { this.matches.set([]); this.loading.set(false); return; }
    this.loading.set(true);
    this.searchTimer = setTimeout(() => void this.performSearch(query, sequence), 250);
  }

  ngOnDestroy(): void {
    if (this.searchTimer) clearTimeout(this.searchTimer);
  }

  private async performSearch(query: string, sequence: number): Promise<void> {
    try {
      const matches = await this.panchanga.cities(query);
      if (sequence === this.searchSequence) this.matches.set(matches.slice(0, 8));
    } catch {
      if (sequence === this.searchSequence) {
        this.matches.set([]);
        this.searchError.set('Place search is unavailable. Check your connection and try again.');
      }
    } finally {
      if (sequence === this.searchSequence) this.loading.set(false);
    }
  }

  choose(place: PanchangaCity): void {
    this.query.set(place.city);
    this.selected.set(place);
    this.matches.set([]);
    this.searchError.set(null);
    this.placeChange.emit(place);
  }
}
