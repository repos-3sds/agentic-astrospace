import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'as-mobile-readings',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <a class="mrd-back" [routerLink]="['/m','chart']"><img src="mobile/back.svg" alt="" /><span>Your Chart</span></a>
    <main class="mrd-body">
      <header><h1>Readings</h1><p>Generated predictions — and how they actually turned out.</p></header>
      <a class="mrd-track" [routerLink]="['/m','readings','accuracy']"><span>↗</span><span><b>18 of 24 held up</b><small>Your track record so far — tap to review</small></span><img src="mobile/chevron.svg" alt="" /></a>
      <nav class="mrd-tabs">@for (tab of ['Today','This week','This year']; track tab) { <button type="button" [class.on]="range() === tab" (click)="range.set(tab)">{{ tab }}</button> }</nav>
      <article class="mrd-reading"><div><b>{{ range() === 'Today' ? 'TODAY · 25 JULY' : range() === 'This year' ? 'YEAR AHEAD · 2026' : 'WEEK OF 20–26 JULY' }}</b><em>CURRENT · v{{ version() }}</em></div><p>{{ readingText() }}</p><hr /><footer><small>Generated 20 Jul · 2 saved versions</small><span>★ ★ ★ ★ ☆</span></footer></article>
      <div class="mrd-actions"><button>Saved versions</button><button class="ink" (click)="generate()">Generate new</button></div>
      <p class="mrd-title">EARLIER</p>
      <article class="mrd-earlier"><span><b>Week of 13–19 July</b><small>Generated 13 Jul</small></span><em>5 OF 6 HELD</em></article>
      <article class="mrd-earlier"><span><b>Year ahead · 2026</b><small>Generated 2 Jan</small></span><em class="progress">IN PROGRESS</em></article>
    </main>
  `,
  styleUrl: './readings.component.scss',
})
export class ReadingsComponent {
  readonly range = signal('This week');
  readonly version = signal(2);
  protected readingText(): string {
    if (this.range() === 'Today') return 'A steady day for finishing what is already open. Keep the evening light and unhurried.';
    if (this.range() === 'This year') return 'A year of measured consolidation, with the strongest progress arriving through patient work and reliable alliances.';
    return 'A week that rewards follow-through over new starts. Mid-week brings a useful conversation about work; keep financial commitments for after the weekend.';
  }
  protected generate(): void { this.version.update((value) => value + 1); }
}
