import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'as-full-transits',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <a class="mtrf-back" [routerLink]="['/m','chart']"><img src="mobile/back.svg" alt="" /><span>Your Chart</span></a>
    <main class="mtrf-body">
      <header><h1>Full Transits</h1><p>Gochara with vedha and Ashtakavarga transit weighting</p></header>
      <nav class="mtrf-tabs"><a [routerLink]="['/m','transits']">Gochara</a><span>Full Transits</span></nav>
      <p class="mtrf-title">CURRENT POSITIONS · EFFECTIVE SEVERITY</p>
      <section class="mtrf-list">@for (row of positions; track row[0]) { <div><span><b>{{ row[0] }}</b><small>{{ row[1] }}</small></span><em>AV {{ row[2] }}</em>@if (row[3]) { <i>VEDHA</i> }</div> }</section>
      <p class="mtrf-title">KEY ASPECTS</p>
      <section class="mtrf-copy"><p>• Transit Saturn aspects natal Moon (3rd drishti) — steady but effortful.</p><p>• Transit Jupiter trines natal Sun — visibility and support.</p></section>
      <p class="mtrf-title">NEXT 30 DAYS</p>
      <section class="mtrf-events">@for (row of events; track row[0]) { <div [attr.data-tone]="row[2]"><i></i><small>{{ row[0] }}</small><p>{{ row[1] }}</p></div> }</section>
    </main>
  `,
  styleUrl: './full-transits.component.scss',
})
export class FullTransitsComponent {
  readonly positions = [['Saturn', 'Aquarius · 10th', '4', ''], ['Jupiter', 'Taurus · 1st', '6', ''], ['Rahu', 'Pisces · 11th', '3', 'vedha'], ['Ketu', 'Virgo · 5th', '5', '']];
  readonly events = [['2 Aug', 'Moon transits natal 7th — relationship focus', 'bad'], ['14 Aug', 'Mercury turns retrograde — recheck contracts', 'warn'], ['29 Aug', 'Venus enters your 1st — a lighter, social stretch', 'good']];
}
