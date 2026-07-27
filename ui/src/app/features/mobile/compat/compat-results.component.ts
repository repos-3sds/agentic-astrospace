import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { PreferencesService } from '../../../core/preferences.service';

@Component({
  selector: 'as-compat-results',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <a class="mcor-back" [routerLink]="['/m','compat']"><img src="mobile/back.svg" alt="" /><span>Compatibility</span></a>
    <main class="mcor-body">
      <section class="mcor-score"><b>LAKSHMI × RAVI</b><div><strong>{{ total() }}</strong><span>/ {{ maximum() }}</span></div><h1>A strong, workable match</h1><p>Good compatibility across communication and temperament — two points to be mindful of below.</p></section>
      <p class="mcor-title">WHAT MATTERS MOST HERE</p>
      <section class="mcor-list">@for (row of visibleKootas(); track row[0]) { <div><b>{{ row[0] }}</b><span>{{ row[1] }} / {{ row[2] }}</span></div> }</section>
      @if (preferences.experienceMode() === 'practitioner') {
        <p class="mcor-title">INPUTS &amp; CANCELLATIONS</p>
        <section class="mcor-flag"><p>D1 + D9 compared · Nadi/Bhakoot cancellation rules evaluated · Lahiri · whole-sign</p></section>
      }
      <p class="mcor-title">FLAGS TO KNOW</p>
      <section class="mcor-flag"><div><b>Manglik</b><em>MATCHED · NOT A CONCERN</em></div><p>Both charts carry a mild Manglik influence — when both sides do, tradition treats it as self-cancelling.</p></section>
      <div class="mcor-actions"><button type="button" (click)="share()">Share report</button><a [routerLink]="['/m','muhurta']">Find a muhurtham</a></div>
    </main>
  `,
  styleUrl: './compat-results.component.scss',
})
export class CompatResultsComponent {
  protected readonly preferences = inject(PreferencesService);
  readonly kootas: [string, number, number][] = [['Nadi (health, genetics)', 8, 8], ['Bhakoot (family harmony)', 7, 7], ['Graha Maitri (mental compatibility)', 4, 5], ['Gana (temperament)', 6, 6], ['Varna', 1, 1], ['Vashya', 1, 2], ['Tara', 1, 3], ['Yoni', 0, 4]];
  readonly total = computed(() => this.kootas.reduce((sum, row) => sum + row[1], 0));
  readonly maximum = computed(() => this.kootas.reduce((sum, row) => sum + row[2], 0));
  readonly visibleKootas = computed(() =>
    this.preferences.experienceMode() === 'practitioner' ? this.kootas : this.kootas.slice(0, 4),
  );
  protected share(): void { void navigator.clipboard?.writeText(`Lakshmi × Ravi: ${this.total()} / ${this.maximum()}`); }
}
