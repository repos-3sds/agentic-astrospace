import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  OnDestroy,
  Output,
  computed,
  inject,
  input,
  signal,
} from '@angular/core';

import { KundliPayload, PanchangaCity } from '../../../core/models';
import { PanchangaService } from '../../../core/panchanga.service';
import { PROFILE_RELATIONSHIPS, normalizeProfileRelationship } from '../settings/profile-fields';

/** Which birth field a validation message belongs under. */
type BirthField = 'name' | 'date' | 'time' | 'place';

/**
 * The one birth-details form (flow audit 2026-10-15, item 5.1).
 *
 * Onboarding, Add / Edit profile, Compatibility › Add a person and Settings ›
 * Birth details each had their own form: one took the city as free text plus
 * a raw country code and saved anything, one had no approximate-time option,
 * one reported only the last error, and each dressed its fields differently.
 * This component owns the fields, the place search and the validation; the
 * screen around it owns the headline, what happens to the payload and where
 * to go next.
 *
 * Time of birth is the field everything else depends on: the ascendant moves
 * a degree every four minutes, so an hour's error changes the rising sign and
 * with it every house. Hence "Don't know the exact time? Use a gentle
 * estimate" sitting directly under the field: the honest path has to be as
 * easy as the confident one, or people guess. The admission travels as
 * `birth_time_accuracy`, which the provenance sheet reports for as long as
 * the chart exists.
 *
 * Place is a lookup, not free text: a chart needs coordinates and a timezone
 * at the birth instant, and "Mumbaii" typed into a string field is neither.
 * The server refuses what it cannot resolve; the form refuses first.
 */
@Component({
  selector: 'as-birth-details-form',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <form class="form" novalidate (submit)="onSubmit($event)">
      <div class="fields">
        <div class="group">
          <label class="field-label" for="bdf-name">{{ nameLabel }}</label>
          <div class="field" [class.is-invalid]="fieldErrors().name">
            <img src="mobile/field-who.svg" alt="" aria-hidden="true" />
            <input
              id="bdf-name"
              type="text"
              autocomplete="name"
              [value]="name()"
              [attr.aria-invalid]="fieldErrors().name ? 'true' : null"
              [attr.aria-describedby]="fieldErrors().name ? 'bdf-name-error' : null"
              (input)="onFieldInput('name', $any($event.target).value)"
            />
          </div>
          @if (fieldErrors().name; as message) {
            <p class="field-error" id="bdf-name-error" role="alert">{{ message }}</p>
          }
        </div>

        @if (!lockRelation) {
          <div class="group">
            <label class="field-label" for="bdf-relation">RELATIONSHIP</label>
            <div class="field">
              <img src="mobile/nav-check-square.svg" alt="" aria-hidden="true" />
              <select id="bdf-relation" [value]="relation()" (change)="relation.set($any($event.target).value)">
                @for (option of relationOptions(); track option.value) {
                  <option [value]="option.value" [selected]="option.value === relation()">{{ option.label }}</option>
                }
              </select>
            </div>
          </div>
        }

        <div class="group">
          <label class="field-label" for="bdf-date">DATE OF BIRTH</label>
          <div class="field" [class.is-invalid]="fieldErrors().date">
            <img src="mobile/field-date.svg" alt="" aria-hidden="true" />
            <input
              id="bdf-date"
              type="date"
              [max]="today"
              [value]="date()"
              [attr.aria-invalid]="fieldErrors().date ? 'true' : null"
              [attr.aria-describedby]="fieldErrors().date ? 'bdf-date-error' : null"
              (input)="onFieldInput('date', $any($event.target).value)"
            />
          </div>
          @if (fieldErrors().date; as message) {
            <p class="field-error" id="bdf-date-error" role="alert">{{ message }}</p>
          }
        </div>

        <div class="group">
          <label class="field-label" for="bdf-time">TIME OF BIRTH</label>
          <div class="field" [class.is-invalid]="fieldErrors().time">
            <img src="mobile/field-time.svg" alt="" aria-hidden="true" />
            <input
              id="bdf-time"
              type="time"
              [value]="time()"
              [attr.aria-invalid]="fieldErrors().time ? 'true' : null"
              [attr.aria-describedby]="fieldErrors().time ? 'bdf-time-error' : null"
              (input)="onFieldInput('time', $any($event.target).value)"
            />
          </div>
          @if (fieldErrors().time; as message) {
            <p class="field-error" id="bdf-time-error" role="alert">{{ message }}</p>
          }
          <!--
            Directly under the field, not in help text: an hour's error moves
            the ascendant a whole sign, so the honest path has to be the easy one.
          -->
          @if (approximate()) {
            <p class="approx is-on">
              <span>Estimated time. Rising sign, houses and dasha dates will be marked as estimates.</span>
              <button class="approx-action" type="button" (click)="useExact()">I know the exact time</button>
            </p>
          } @else {
            <p class="approx">
              <span>Don’t know the exact time?</span>
              <button class="approx-action" type="button" (click)="useApproximate()">Use a gentle estimate</button>
            </p>
          }
        </div>

        <div class="group">
          <label class="field-label" for="bdf-place">PLACE OF BIRTH</label>
          <div
            class="field"
            [class.is-active]="placeQuery().length > 0 && !chosenPlace()"
            [class.is-invalid]="fieldErrors().place"
          >
            <img [src]="placeQuery() && !chosenPlace() ? 'mobile/pin-accent.svg' : 'mobile/pin.svg'" alt="" aria-hidden="true" />
            <input
              id="bdf-place"
              type="text"
              autocomplete="off"
              placeholder="Search city or town"
              [value]="placeQuery()"
              [attr.aria-expanded]="matches().length > 0"
              [attr.aria-invalid]="fieldErrors().place ? 'true' : null"
              [attr.aria-describedby]="fieldErrors().place ? 'bdf-place-error' : null"
              aria-controls="bdf-place-results"
              (input)="onPlaceInput($any($event.target).value)"
            />
          </div>
          @if (fieldErrors().place; as message) {
            <p class="field-error" id="bdf-place-error" role="alert">{{ message }}</p>
          }
          @if (chosenPlace(); as place) {
            @if (place.timezone) {
              <p class="place-status">{{ place.label || place.nation }} · {{ place.timezone }}</p>
            }
          }
          @if (placeLoading()) {
            <p class="place-status" role="status">Searching places…</p>
          }
          <!-- One message under the field: the submit error already says what to do. -->
          @if (!fieldErrors().place && placeError(); as message) {
            <p class="field-error" role="alert">{{ message }}</p>
          }
          @if (matches().length > 0) {
            <ul class="matches" id="bdf-place-results" role="listbox" aria-label="Matching places">
              @for (m of matches(); track m.label + m.lat + m.lng; let first = $first) {
                <li>
                  <button
                    class="match"
                    type="button"
                    role="option"
                    [attr.aria-selected]="first"
                    [class.is-first]="first"
                    (click)="choosePlace(m)"
                  >
                    <img src="mobile/pin.svg" alt="" aria-hidden="true" />
                    <span class="match-text">
                      <span class="match-city">{{ m.city }}</span>
                      <span class="match-region">{{ m.label || (m.nation + ' · ' + m.timezone) }}</span>
                    </span>
                  </button>
                </li>
              }
            </ul>
          }
        </div>
      </div>

      <div class="actions">
        @if (error) { <p class="form-error" role="alert">{{ error }}</p> }
        <button class="submit" type="submit" [disabled]="saving">
          @if (submitIcon) { <img [src]="submitIcon" alt="" aria-hidden="true" /> }
          <span>{{ saving ? busyLabel : submitLabel }}</span>
        </button>
      </div>
    </form>
  `,
  styleUrl: './birth-details-form.component.scss',
})
export class BirthDetailsFormComponent implements OnDestroy {
  private readonly panchanga = inject(PanchangaService);

  /** Label over the name field: "NAME", or onboarding's "WHO IS THIS FOR?". */
  @Input() nameLabel = 'NAME';
  /** When set, the relationship is fixed (onboarding: "self") and the select is hidden. */
  @Input() lockRelation: string | null = null;
  /**
   * Hide "Myself" when the account already has a self profile and this isn't
   * it. A signal input, because `relationOptions` is computed from it.
   */
  readonly hideSelf = input(false);
  @Input() submitLabel = 'Save';
  @Input() busyLabel = 'Saving…';
  @Input() submitIcon: string | null = null;
  /** The screen's save in flight: the CTA shows `busyLabel` and refuses a second tap. */
  @Input() saving = false;
  /** What the server said when the save failed, shown above the CTA. */
  @Input() error: string | null = null;

  @Input() set initial(value: Partial<KundliPayload> | null) {
    if (!value) return;
    if (value.name !== undefined) this.name.set(value.name);
    if (value.relation !== undefined) this.relation.set(normalizeProfileRelationship(value.relation));
    if (value.birth_year && value.birth_month && value.birth_day) {
      this.date.set(`${value.birth_year}-${pad(value.birth_month)}-${pad(value.birth_day)}`);
    }
    if (value.birth_hour !== undefined && value.birth_minute !== undefined) {
      this.time.set(`${pad(value.birth_hour)}:${pad(value.birth_minute)}`);
    }
    if (value.birth_time_accuracy !== undefined) this.approximate.set(value.birth_time_accuracy !== 'exact');
    if (value.birth_city) {
      // A saved place is trusted as-is; the server resolved it when it was
      // saved. Editing the field invalidates it, as it should.
      this.placeQuery.set(value.birth_city);
      this.chosenPlace.set({
        city: value.birth_city,
        nation: value.birth_nation ?? 'IN',
        timezone: '',
        lat: NaN,
        lng: NaN,
        label: value.birth_city,
      });
    }
  }

  @Output() readonly submitted = new EventEmitter<KundliPayload>();

  readonly name = signal('');
  readonly relation = signal('friend');
  readonly date = signal('');
  readonly time = signal('');
  /** Whether the time was entered exactly or rounded — reported in provenance. */
  readonly approximate = signal(false);

  readonly placeQuery = signal('');
  readonly chosenPlace = signal<PanchangaCity | null>(null);
  readonly matches = signal<PanchangaCity[]>([]);
  readonly placeLoading = signal(false);
  readonly placeError = signal<string | null>(null);

  readonly fieldErrors = signal<Partial<Record<BirthField, string>>>({});

  readonly relationOptions = computed(() =>
    PROFILE_RELATIONSHIPS.filter((option) => option.value !== 'self' || !this.hideSelf() || this.relation() === 'self'),
  );

  /** Today's date in the picker's format, so a future birth date can't be picked. */
  protected readonly today = new Date().toISOString().slice(0, 10);

  private placeSearchSeq = 0;
  private placeSearchTimer: ReturnType<typeof setTimeout> | null = null;

  ngOnDestroy(): void {
    if (this.placeSearchTimer) clearTimeout(this.placeSearchTimer);
  }

  /** Typing into a field clears its own message, never the others'. */
  protected onFieldInput(field: 'name' | 'date' | 'time', value: string): void {
    ({ name: this.name, date: this.date, time: this.time })[field].set(value);
    this.clearError(field);
  }

  /**
   * Rounds to a morning hour and records that it was rounded. The flag is the
   * point — a chart cast from a guess must keep saying so.
   */
  protected useApproximate(): void {
    this.approximate.set(true);
    this.time.set(this.time() || '06:00');
    this.clearError('time');
  }

  protected useExact(): void {
    this.approximate.set(false);
  }

  protected onPlaceInput(value: string): void {
    this.placeQuery.set(value);
    this.chosenPlace.set(null);
    this.placeError.set(null);
    this.clearError('place');
    const q = value.trim();
    const seq = ++this.placeSearchSeq;
    if (this.placeSearchTimer) clearTimeout(this.placeSearchTimer);
    if (q.length < 2) {
      this.matches.set([]);
      this.placeLoading.set(false);
      return;
    }
    this.placeLoading.set(true);
    this.placeSearchTimer = setTimeout(() => void this.searchPlaces(q, seq), 250);
  }

  private async searchPlaces(query: string, seq: number): Promise<void> {
    try {
      const matches = await this.panchanga.cities(query);
      if (seq !== this.placeSearchSeq) return;
      this.matches.set(matches.slice(0, 8));
      if (matches.length === 0) this.placeError.set('No place matches that yet. Try the nearest town or city.');
    } catch {
      if (seq === this.placeSearchSeq) {
        this.matches.set([]);
        this.placeError.set('Could not search places. Check your connection and try again.');
      }
    } finally {
      if (seq === this.placeSearchSeq) this.placeLoading.set(false);
    }
  }

  protected choosePlace(match: PanchangaCity): void {
    this.chosenPlace.set(match);
    this.placeQuery.set(match.city);
    this.matches.set([]);
    this.placeError.set(null);
    this.clearError('place');
  }

  protected onSubmit(event: Event): void {
    event.preventDefault();
    const payload = this.validate();
    if (payload) this.submitted.emit(payload);
  }

  /** The payload the API takes, or null with every field's message set at once. */
  validate(): KundliPayload | null {
    const errors: Partial<Record<BirthField, string>> = {};
    const name = this.name().trim();
    if (!name) errors.name = 'Add a name for this chart.';

    const [year, month, day] = this.date().split('-').map(Number);
    if (!year || !month || !day) errors.date = 'Pick the date of birth.';
    else if (this.date() > this.today) errors.date = 'The date of birth can’t be in the future.';
    else if (year < 1200) errors.date = 'Pick a date of birth after the year 1200.';

    const [hour, minute] = this.time().split(':').map(Number);
    if (!this.time() || Number.isNaN(hour) || Number.isNaN(minute)) {
      errors.time = 'Enter the time of birth, or use a gentle estimate.';
    }

    const place = this.chosenPlace();
    if (!place) {
      errors.place = this.placeQuery().trim()
        ? 'Choose the birth place from the search results.'
        : 'Search for the place of birth.';
    }

    this.fieldErrors.set(errors);
    if (Object.keys(errors).length > 0 || !place) return null;
    return {
      name,
      relation: this.lockRelation ?? this.relation(),
      birth_year: year,
      birth_month: month,
      birth_day: day,
      birth_hour: hour,
      birth_minute: minute,
      birth_city: place.city,
      birth_nation: (place.nation || 'IN').toUpperCase(),
      birth_time_accuracy: this.approximate() ? 'approximate' : 'exact',
    };
  }

  private clearError(field: BirthField): void {
    if (!this.fieldErrors()[field]) return;
    this.fieldErrors.update((errors) => {
      const next = { ...errors };
      delete next[field];
      return next;
    });
  }
}

function pad(value: number): string {
  return String(value).padStart(2, '0');
}
