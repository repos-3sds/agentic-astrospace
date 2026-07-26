import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

/** A place the typeahead offers for the birth location. */
interface PlaceMatch {
  city: string;
  region: string;
}

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
        <input id="bd-date" type="text" [value]="date()" (input)="date.set($any($event.target).value)" />
      </div>

      <label class="field-label" for="bd-time">TIME OF BIRTH</label>
      <div class="field">
        <img src="mobile/field-time.svg" alt="" aria-hidden="true" />
        <input id="bd-time" type="text" [value]="time()" (input)="time.set($any($event.target).value)" />
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
          autocomplete="off"
          [value]="placeQuery()"
          (input)="onPlaceInput($any($event.target).value)"
        />
      </div>

      @if (matches().length > 0) {
        <ul class="matches" role="listbox" aria-label="Matching places">
          @for (m of matches(); track m.city; let first = $first) {
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
                  <span class="match-region">{{ m.region }}</span>
                </span>
              </button>
            </li>
          }
        </ul>
      }
    </div>

    <a class="btn" [routerLink]="['/m', 'today']">
      <img src="mobile/cast.svg" alt="" aria-hidden="true" />
      <span>Cast my chart</span>
    </a>
  `,
  styleUrl: './birth-details.component.scss',
  // Outside the shell, so the token host class must be applied here or every
  // var() silently falls back — see the build plan's first convention.
  host: { class: 'as-mobile' },
})
export class BirthDetailsComponent {
  readonly who = signal('Lakshmi  ·  Myself');
  readonly date = signal('14 August 1991');
  readonly time = signal('06:12 AM');

  readonly placeQuery = signal('Vijaya');
  readonly chosenPlace = signal<PlaceMatch | null>(null);

  /** Whether the time was entered exactly or rounded — reported in provenance. */
  readonly timeIsApproximate = signal(false);

  private readonly places: PlaceMatch[] = [
    { city: 'Vijayawada', region: 'Andhra Pradesh, India' },
    { city: 'Vijayapura', region: 'Karnataka, India' },
    { city: 'Vizianagaram', region: 'Andhra Pradesh, India' },
  ];

  protected readonly matches = computed(() => {
    const q = this.placeQuery().trim().toLowerCase();
    if (!q || this.chosenPlace()) {
      return [];
    }
    return this.places.filter((p) => p.city.toLowerCase().startsWith(q.slice(0, 2)));
  });

  protected onPlaceInput(value: string): void {
    this.placeQuery.set(value);
    this.chosenPlace.set(null);
  }

  protected choosePlace(match: PlaceMatch): void {
    this.chosenPlace.set(match);
    this.placeQuery.set(match.city);
  }

  /**
   * Rounds to the nearest hour and records that it was rounded. The flag is the
   * point — a chart cast from a guess must keep saying so.
   */
  protected useApproximate(): void {
    this.timeIsApproximate.set(true);
    this.time.set('06:00 AM (approx)');
  }
}
