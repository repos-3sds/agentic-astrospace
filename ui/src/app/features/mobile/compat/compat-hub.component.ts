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
      <section class="mco-empty"><div aria-hidden="true">♡</div><b>No checks yet</b><p>Add another profile to compute your first match.</p></section>
    </main>
  `,
  styleUrl: './compat-hub.component.scss',
})
export class CompatHubComponent {}
