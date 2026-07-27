import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'as-compat-hub',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <a class="mco-back" [routerLink]="['/m','chart']"><img src="mobile/back.svg" alt="" /><span>Your Chart</span></a>
    <main class="mco-body">
      <header><h1>Compatibility</h1><p>Ashta Koota matching — 36 points, computed honestly</p></header>
      <section class="mco-how"><b>HOW THIS WORKS</b><p>We compare two charts across the 8 classical kootas (36 points total), flag doshas honestly, and check for traditional cancellations — no fear, no upsell.</p></section>
      <a class="mco-primary" [routerLink]="['/m','compat','add']"><span>＋</span>Check a new match</a>
      <p class="mco-label">RECENT CHECKS</p>
      <a class="mco-recent" [routerLink]="['/m','compat','results']"><span class="mco-avatar">R</span><span><b>Lakshmi × Ravi</b><small>28 / 36 · Checked 2 weeks ago</small></span><img src="mobile/chevron.svg" alt="" /></a>
    </main>
  `,
  styleUrl: './compat-hub.component.scss',
})
export class CompatHubComponent {}
