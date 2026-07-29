import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FestivalSheetComponent } from './festival-sheet.component';
import { PreferencesService } from '../../../core/preferences.service';

@Component({
  selector: 'as-mobile-calendar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, FestivalSheetComponent],
  template: `
    <header class="mcal-top"><h1>Calendar</h1><div><button aria-label="Previous month"><img src="mobile/back.svg" alt="" /></button><b>July 2026</b><button class="mcal-next" aria-label="Next month"><img src="mobile/back.svg" alt="" /></button></div></header>
    <main class="mcal-body">
      <section class="mcal-grid">
        @for (day of weekdays; track day) { <span class="mcal-weekday">{{ day }}</span> }
        @for (_ of blanks; track $index) { <span></span> }
        @for (day of days; track day) {
          @if (day === 25) { <a class="mcal-selected" [routerLink]="['/m','calendar','day']">{{ day }}</a> }
          @else { <span [class.mcal-event]="day === 29 || day === 30">{{ day }}</span> }
        }
      </section>
      <p class="mcal-eyebrow">UPCOMING OBSERVANCES</p>
      @if (preferences.experienceMode() === 'practitioner') {
        <p class="mcal-eyebrow">LAHIRI · LOCAL TZ · AMANTA · SUNRISE CUT-OFF</p>
      }
      <button class="mcal-observance" type="button" (click)="festivalOpen.set(true)">
        <span class="mcal-date-tile"><b>29</b><small>Jul</small></span>
        <span><b>Naga Panchami</b><small>Prep: temple visit, offerings at dawn</small><em>4 days away</em></span>
      </button>
      <article class="mcal-observance">
        <span class="mcal-date-tile"><b>30</b><small>Jul</small></span>
        <span><b>Varalakshmi Vratam</b><small>Prep: begin fasting preparations 2 days ahead</small><em>5 days away</em></span>
      </article>
    </main>
    @if (festivalOpen()) { <as-festival-sheet (dismissed)="festivalOpen.set(false)" /> }
  `,
  styleUrl: './calendar.component.scss',
})
export class CalendarComponent {
  protected readonly preferences = inject(PreferencesService);
  readonly weekdays = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
  readonly blanks = [0, 1, 2];
  readonly days = Array.from({ length: 31 }, (_, index) => index + 1);
  readonly festivalOpen = signal(false);
}
