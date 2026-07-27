import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'as-reading-accuracy',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <a class="mra-back" [routerLink]="['/m','readings']"><img src="mobile/back.svg" alt="" /><span>Readings</span></a>
    <main class="mra-body">
      <header><h1>Track record</h1><p>We keep score honestly — including when we get it wrong.</p></header>
      <section class="mra-summary"><div><span><b>{{ heldRate() }}</b>%</span><small>{{ totalClaims() }} claims reviewed</small></div><div class="mra-meter">@for (item of counts; track item.label) { <i [attr.data-tone]="item.tone" [style.flex]="item.count"></i> }</div><footer>@for (item of counts; track item.label) { <span><i [attr.data-tone]="item.tone"></i>{{ item.count }} {{ item.label }}</span> }</footer></section>
      <nav class="mra-tabs"><button class="on">To review</button><button>All</button></nav>
      @if (!reviewed()) {
        <p class="mra-title accent">AWAITING YOUR CALL</p>
        <section class="mra-claim"><div><em>CAREER</em><small>Window: 20–26 Jul</small></div><blockquote>“A useful work conversation lands mid-week — likely with someone senior.”</blockquote><p>Did this happen?</p><footer><button (click)="review('accurate')">Yes</button><button (click)="review('partly')">Partly</button><button (click)="review('missed')">No</button></footer></section>
      }
      <p class="mra-title">ALREADY REVIEWED</p>
      @for (claim of reviewedClaims(); track claim[0]) { <article class="mra-reviewed"><div><small>{{ claim[0] }}</small><em [attr.data-tone]="claim[2]">{{ claim[2] === 'accurate' ? 'ACCURATE' : claim[2] === 'partly' ? 'PARTLY' : 'MISSED' }}</em></div><p>{{ claim[1] }}</p></article> }
    </main>
  `,
  styleUrl: './accuracy.component.scss',
})
export class AccuracyComponent {
  readonly reviewed = signal(false);
  readonly counts = [
    { label: 'accurate', count: 14, tone: 'good' }, { label: 'partly', count: 4, tone: 'warn' },
    { label: 'missed', count: 4, tone: 'bad' }, { label: 'n/a', count: 2, tone: 'neutral' },
  ];
  readonly baseClaims: [string, string, string][] = [['WEALTH', '“A delayed payment clears before month end.”', 'accurate'], ['HEALTH', '“Low energy in the first half of the week.”', 'missed']];
  readonly latest = signal<[string, string, string] | null>(null);
  readonly totalClaims = computed(() => this.counts.reduce((sum, item) => sum + item.count, 0));
  readonly heldRate = computed(() => Math.round((this.counts[0].count + this.counts[1].count) / this.totalClaims() * 100));
  readonly reviewedClaims = computed(() => this.latest() ? [this.latest()!, ...this.baseClaims] : this.baseClaims);
  protected review(outcome: string): void { this.latest.set(['CAREER', '“A useful work conversation lands mid-week — likely with someone senior.”', outcome]); this.reviewed.set(true); }
}
