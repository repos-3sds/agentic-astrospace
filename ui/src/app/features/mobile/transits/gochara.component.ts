import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TransitDetail, TransitDetailComponent } from './transit-detail.component';

@Component({
  selector: 'as-gochara',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, TransitDetailComponent],
  template: `
    <a class="mtr-back" [routerLink]="['/m','chart']"><img src="mobile/back.svg" alt="" /><span>Your Chart</span></a>
    <main class="mtr-body">
      <header><h1>What’s moving now</h1><p>Gochara — how today’s sky sits against your chart</p></header>
      <nav class="mtr-tabs"><span>Gochara</span><a [routerLink]="['/m','transits','full']">Full Transits</a></nav>
      <section class="mtr-overall"><b>OVERALL</b><h2>A settling, steady stretch</h2><p>Jupiter and Saturn are both supportive from here — good for follow-through on things already in motion.</p></section>
      <p class="mtr-title">PLANET BY PLANET</p>
      @for (row of planets; track row[0]) {
        <button type="button" class="mtr-card" (click)="open(row)"><div><b>{{ row[0] }}</b><em [attr.data-tone]="row[4]">{{ row[1] }}</em></div><small>{{ row[2] }}</small><p>{{ row[3] }}</p></button>
      }
      <p class="mtr-hint">Switch to Full Transits for aspects, timeline, and strength weighting</p>
    </main>
    @if(selected()){<as-transit-detail [detail]="selected()!" (dismissed)="selected.set(null)" />}
  `,
  styleUrl: './gochara.component.scss',
})
export class GocharaComponent {
  readonly planets = [
    ['Saturn in Aquarius', 'MILD FRICTION', 'Transiting your 10th house — career, status', 'Steady, unglamorous effort pays off now — avoid shortcuts at work.', 'warn'],
    ['Jupiter in Taurus', 'SUPPORTIVE', 'Transiting your 1st house — self, vitality', 'A gentle boost to confidence and visibility — good window to start things.', 'good'],
    ['Rahu in Pisces', 'WATCH', 'Transiting your 11th house — gains, community', 'Tempting shortcuts around money or networks — verify before you commit.', 'warn'],
  ];
  readonly selected = signal<TransitDetail|null>(null);
  protected open(row:string[]):void { this.selected.set({planet:row[0],glyph:row[0].slice(0,2),position:row[2],period:'Current slow transit',meaning:row[3],guidance:'Work with the indicated pace and verify important decisions against real-world information.',evidence:[row[2],'Natal-house placement','Ashtakavarga and vedha weighting']}); }
}
