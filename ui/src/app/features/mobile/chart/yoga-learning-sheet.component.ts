import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { SheetComponent } from '../sheet/sheet.component';
import { Combination } from './combinations';

/**
 * The full card for one yoga or dosha (Figma node 41:210, rebuilt
 * 2026-10-29): what it is, why this chart has it, what softens or weakens
 * it, what it can mean, what to do and what to avoid. No book sources on
 * screen; Practitioner adds the classical rule and the engine's triggers.
 */
@Component({
  selector: 'as-yoga-learning-sheet',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SheetComponent],
  template: `
    @let d = detail();
    <as-sheet (dismissed)="dismissed.emit()">
      <header class="head">
        <p class="eyebrow">{{ d.kind === 'dosha' ? 'DOSHA' : 'YOGA' }} · {{ d.tag === 'Cancelled' ? 'CHECKED AND CANCELLED' : d.flag ? 'A FLAG, NOT A VERDICT' : 'A STRENGTH' }}</p>
        <h2>{{ d.title }}</h2>
        <p class="tagline"><span class="tag" [attr.data-tone]="d.tone">{{ d.tag }}</span>@if (d.howCommon) {<span class="common">{{ d.howCommon }}</span>}</p>
      </header>

      <section>
        <h3>What it is</h3>
        <p class="body">{{ d.what }}</p>
      </section>

      @if (d.why.length) {
        <section class="why">
          <h3>Why you have it</h3>
          @for (line of d.why; track $index) { <p>{{ line }}</p> }
        </section>
      }

      @if (d.softens.length) {
        <section class="softens">
          <h3>{{ d.tag === 'Cancelled' ? 'Why it is cancelled' : 'What softens it' }}</h3>
          @for (line of d.softens; track $index) {
            <p><img src="mobile/cancellation-check.svg" alt="" aria-hidden="true" />{{ line }}</p>
          }
        </section>
      }
      @if (d.weakened.length) {
        <section>
          <h3>What weakens it</h3>
          @for (line of d.weakened; track $index) { <p class="body small">{{ line }}</p> }
        </section>
      }

      @if (d.impact) {
        <section>
          <h3>What it can mean for you</h3>
          <p class="body">{{ d.impact }}</p>
        </section>
      }

      @if (d.do.length || d.avoid.length) {
        <div class="do-avoid">
          @if (d.do.length) {
            <section class="do">
              <h3>Do</h3>
              <ul>@for (line of d.do; track $index) { <li>{{ line }}</li> }</ul>
            </section>
          }
          @if (d.avoid.length) {
            <section class="avoid">
              <h3>Avoid</h3>
              <ul>@for (line of d.avoid; track $index) { <li>{{ line }}</li> }</ul>
            </section>
          }
        </div>
      }

      @if (d.alsoChecked.length) {
        <section>
          <h3>Also checked</h3>
          @for (line of d.alsoChecked; track $index) { <p class="body small muted">{{ line }}</p> }
        </section>
      }
      @if (d.convention) { <p class="note">{{ d.convention }}</p> }

      @if (practitioner()) {
        <section class="practitioner">
          <h3>Classical rule</h3>
          <p class="body small">{{ d.classical }}</p>
          @if (d.triggers.length) {
            <h3>Engine check</h3>
            <ul>@for (line of d.triggers; track $index) { <li>{{ line }}</li> }</ul>
          }
        </section>
      }
      <button class="got-it" type="button" (click)="dismissed.emit()">Got it</button>
    </as-sheet>
  `,
  styleUrl: './yoga-learning-sheet.component.scss',
})
export class YogaLearningSheetComponent {
  readonly detail = input.required<Combination>();
  readonly practitioner = input(false);
  readonly dismissed = output<void>();
}
