import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'as-calendar-day',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <a class="mcald-back" [routerLink]="['/m','calendar']"><img src="mobile/back.svg" alt="" /><span>Calendar</span></a>
    <main class="mcald-body">
      <header><h1>Saturday, 25 July</h1><p>Dvitiya · Hasta · Shubha yoga</p></header>
      <section class="mcald-quality"><span><img src="mobile/cancellation-check.svg" alt="" /></span><div><b>Good day for you</b><small>Tarabala favourable · Chandrabala strong</small></div></section>
      <p class="mcald-title accent">DAY TIMELINE</p>
      <section class="mcald-list">
        @for (row of timeline; track row[0]) { <div [class.bad]="row[2] === 'AVOID'"><i></i><span><b>{{ row[0] }}</b><small>{{ row[1] }}</small></span><em>{{ row[2] }}</em></div> }
      </section>
      <p class="mcald-title">DAY CHOGHADIYA</p>
      <section class="mcald-choghadiya">
        @for (row of choghadiya; track row[0]) { <article [attr.data-tone]="row[2]"><b>{{ row[0] }}</b><small>{{ row[1] }}</small></article> }
      </section>
      <p class="mcald-title">ACTIVE PERIOD STACK</p>
      <section class="mcald-stack">
        @for (row of periods; track row[0]) { <div><small>{{ row[0] }}</small><b>{{ row[1] }}</b></div> }
      </section>
    </main>
  `,
  styleUrl: './calendar-day.component.scss',
})
export class CalendarDayComponent {
  readonly timeline = [
    ['Brahma Muhurta', '05:52 – 07:26 AM', 'GOOD'], ['Amrit Kalam', '09:12 – 10:48 AM', 'GOOD'],
    ['Abhijit Muhurta', '11:48 AM – 12:36 PM', 'GOOD'], ['Yamaganda', '01:30 – 03:00 PM', 'AVOID'],
    ['Rahu Kalam', '04:30 – 06:00 PM', 'AVOID'], ['Varjya', '06:20 – 07:10 PM', 'AVOID'],
  ];
  readonly choghadiya = [
    ['Amrit', '06:00–07:30', 'good'], ['Kaal', '07:30–09:00', 'bad'], ['Shubh', '09:00–10:30', 'good'],
    ['Rog', '10:30–12:00', 'bad'], ['Udveg', '12:00–13:30', 'warn'], ['Chal', '13:30–15:00', 'warn'],
  ];
  readonly periods = [['MAHA', 'Venus · 2013–2033'], ['ANTAR', 'Saturn · 2025–2028'], ['PRATYANTAR', 'Venus · Jan–Jul 2026']];
}
