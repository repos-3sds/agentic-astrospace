import { ChangeDetectionStrategy, Component, inject, input, output, signal } from '@angular/core';
import { PanchangaCity } from '../../../core/models';
import { PanchangaService } from '../../../core/panchanga.service';

/**
 * A city search box with a short list of matches, as Settings › Location has.
 * Used where a screen needs a place of its own: the city a reader lives in
 * (onboarding) and the city a muhurta is for ("Where will this happen?").
 */
@Component({
  selector: 'as-city-picker',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <label class="place-search">
      <span>{{ label() }}</span>
      <input
        [id]="inputId()"
        type="search"
        autocomplete="off"
        [value]="query()"
        (input)="onQuery($any($event.target).value)"
        [placeholder]="placeholder()"
      />
    </label>
    @if (searching()) {
      <p class="search-note">Searching cities…</p>
    } @else if (error()) {
      <p class="search-note is-error">{{ error() }}</p>
    } @else if (suggestions().length) {
      <div class="city-list">
        @for (city of suggestions(); track city.city + city.nation + city.timezone) {
          <button type="button" class="city-row" (click)="choose(city)">
            <span>
              <b>{{ city.city }}</b>
              <small>{{ city.nation }} · {{ city.timezone }}</small>
            </span>
            <img src="mobile/chevron.svg" alt="" aria-hidden="true" />
          </button>
        }
      </div>
    }
  `,
  styleUrl: './city-picker.component.scss',
})
export class CityPickerComponent {
  private readonly panchanga = inject(PanchangaService);

  readonly label = input('CITY');
  readonly placeholder = input('Search city');
  readonly inputId = input('city-picker');
  readonly initial = input('');
  readonly picked = output<PanchangaCity>();

  protected readonly query = signal('');
  protected readonly suggestions = signal<PanchangaCity[]>([]);
  protected readonly searching = signal(false);
  protected readonly error = signal<string | null>(null);
  private timer: ReturnType<typeof setTimeout> | null = null;
  private run = 0;

  ngOnInit(): void {
    if (this.initial()) this.query.set(this.initial());
  }

  protected onQuery(value: string): void {
    this.query.set(value);
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(() => void this.search(value), 250);
  }

  protected choose(city: PanchangaCity): void {
    this.query.set(city.label);
    this.suggestions.set([]);
    this.picked.emit(city);
  }

  private async search(value: string): Promise<void> {
    const q = value.trim();
    const run = ++this.run;
    if (q.length < 2) {
      this.suggestions.set([]);
      this.error.set(null);
      return;
    }
    this.searching.set(true);
    this.error.set(null);
    try {
      const cities = await this.panchanga.cities(q, 8);
      if (run === this.run) this.suggestions.set(cities.slice(0, 8));
    } catch (error) {
      if (run === this.run) {
        this.suggestions.set([]);
        this.error.set((error as Error).message);
      }
    } finally {
      if (run === this.run) this.searching.set(false);
    }
  }
}
