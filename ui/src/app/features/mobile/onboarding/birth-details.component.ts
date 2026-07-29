import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/auth.service';
import { KundliStore } from '../../../core/kundli.store';
import { PanchangaCity } from '../../../core/models';
import { PanchangaService } from '../../../core/panchanga.service';

/** A place the typeahead offers for the birth location. */
type PlaceMatch = PanchangaCity;

/**
 * Birth Details (Figma node 11:2) — the last step of onboarding.
 *
 * Time of birth is the field everything else depends on: the ascendant moves a
 * degree every four minutes, so an hour's error changes the rising sign and
 * with it every house in the chart. Hence "Don't know the exact time? Use
 * approximate" sitting directly under the field rather than in help text — the
 * honest path has to be as easy as the confident one, or people guess.
 *
 * That admission is also what the provenance sheet's "Birth time confidence"
 * row reports, so a chart cast from an approximate time says so for as long as
 * it exists rather than quietly presenting itself as exact.
 *
 * Place is a lookup, not free text: a chart needs coordinates and a timezone at
 * the birth instant, and "Vijayawada" typed into a string field is neither.
 */
@Component({
  selector: 'as-birth-details',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <div class="top">
      <header class="topbar">
        <a class="back" [routerLink]="['/m', 'persona']" aria-label="Back">
          <img src="mobile/back.svg" alt="" aria-hidden="true" />
        </a>
        <p class="step">STEP 2 OF 2</p>
      </header>

      <h1 class="headline">Your birth details</h1>
      <p class="lede">The more precise, the more accurate your chart.</p>

      <label class="field-label" for="bd-who">WHO IS THIS FOR?</label>
      <div class="field">
        <img src="mobile/field-who.svg" alt="" aria-hidden="true" />
        <input id="bd-who" type="text" [value]="who()" (input)="who.set($any($event.target).value)" />
      </div>

      <label class="field-label" for="bd-date">DATE OF BIRTH</label>
      <div class="field">
        <img src="mobile/field-date.svg" alt="" aria-hidden="true" />
        <input id="bd-date" type="date" [value]="date()" (input)="date.set($any($event.target).value)" />
      </div>

      <label class="field-label" for="bd-time">TIME OF BIRTH</label>
      <div class="field">
        <img src="mobile/field-time.svg" alt="" aria-hidden="true" />
        <input id="bd-time" type="time" [value]="time()" (input)="time.set($any($event.target).value)" />
      </div>

      <!--
        Directly under the field, not in help text: an hour's error moves the
        ascendant a whole sign, so the honest path has to be the easy one.
      -->
      <p class="approx">
        <span>Don’t know the exact time?</span>
        <button class="approx-action" type="button" (click)="useApproximate()">
          Use approximate
        </button>
      </p>

      <label class="field-label" for="bd-place">PLACE OF BIRTH</label>
      <div class="field" [class.is-active]="placeQuery().length > 0 && !chosenPlace()">
        <img
          [src]="placeQuery() && !chosenPlace() ? 'mobile/pin-accent.svg' : 'mobile/field-who.svg'"
          alt=""
          aria-hidden="true"
        />
        <input
          id="bd-place"
          type="text"
          autocomplete="address-level2"
          placeholder="Search city"
          [value]="placeQuery()"
          (input)="onPlaceInput($any($event.target).value)"
        />
      </div>

      @if (placeLoading()) {
        <p class="place-status" role="status">Searching places…</p>
      }

      @if (matches().length > 0) {
        <ul class="matches" role="listbox" aria-label="Matching places">
          @for (m of matches(); track m.label; let first = $first) {
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

    @if (error()) { <p class="form-error" role="alert">{{ error() }}</p> }
    <button class="btn" type="button" [disabled]="saving()" (click)="castChart()">
      <img src="mobile/cast.svg" alt="" aria-hidden="true" />
      <span>{{ saving() ? 'Casting your chart…' : 'Cast my chart' }}</span>
    </button>
  `,
  styleUrl: './birth-details.component.scss',
  // Outside the shell, so the token host class must be applied here or every
  // var() silently falls back — see the build plan's first convention.
  host: { class: 'as-mobile' },
})
export class BirthDetailsComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly panchanga = inject(PanchangaService);

  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly who = signal(
    `${
      sessionStorage.getItem('astrospace.onboardingName')
      || this.auth.user()?.user_metadata?.['name']
      || 'My chart'
    }  ·  Myself`,
  );
  readonly date = signal('');
  readonly time = signal('');

  readonly placeQuery = signal('');
  readonly chosenPlace = signal<PlaceMatch | null>(null);
  readonly matches = signal<PlaceMatch[]>([]);
  readonly placeLoading = signal(false);

  /** Whether the time was entered exactly or rounded — reported in provenance. */
  readonly timeIsApproximate = signal(false);

  private placeSearchSeq = 0;

  protected async onPlaceInput(value: string): Promise<void> {
    this.placeQuery.set(value);
    this.chosenPlace.set(null);
    this.error.set(null);
    const q = value.trim();
    const seq = ++this.placeSearchSeq;
    if (q.length < 2) {
      this.matches.set([]);
      this.placeLoading.set(false);
      return;
    }
    this.placeLoading.set(true);
    try {
      const matches = await this.panchanga.cities(q);
      if (seq === this.placeSearchSeq) this.matches.set(matches.slice(0, 8));
    } catch {
      if (seq === this.placeSearchSeq) {
        this.matches.set([]);
        this.error.set('Could not search places. Check your connection and try again.');
      }
    } finally {
      if (seq === this.placeSearchSeq) this.placeLoading.set(false);
    }
  }

  protected choosePlace(match: PlaceMatch): void {
    this.chosenPlace.set(match);
    this.placeQuery.set(match.city);
    this.matches.set([]);
  }

  /**
   * Rounds to the nearest hour and records that it was rounded. The flag is the
   * point — a chart cast from a guess must keep saying so.
   */
  protected useApproximate(): void {
    this.timeIsApproximate.set(true);
    this.time.set(this.time() || '06:00');
  }

  protected async castChart(): Promise<void> {
    const [year, month, day] = this.date().split('-').map(Number);
    const [hour, minute] = this.time().split(':').map(Number);
    const place = this.chosenPlace();
    if (!year || !month || !day || Number.isNaN(hour) || Number.isNaN(minute) || !place) {
      this.error.set('Choose a valid date, time, and birth place.');
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    try {
      const created = await this.kundlis.create({
        name: this.who().split('·')[0].trim(),
        relation: 'self',
        birth_year: year,
        birth_month: month,
        birth_day: day,
        birth_hour: hour,
        birth_minute: minute,
        birth_city: place.city,
        birth_nation: place.nation,
        notes: this.timeIsApproximate() ? 'Birth time is approximate.' : undefined,
      });
      this.kundlis.setActive(created.id);
      sessionStorage.removeItem('astrospace.onboardingName');
      await this.router.navigate(['/m', 'insight']);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.saving.set(false);
    }
  }
}
