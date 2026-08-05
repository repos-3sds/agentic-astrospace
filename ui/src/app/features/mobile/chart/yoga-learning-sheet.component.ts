import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { SheetComponent } from '../sheet/sheet.component';

export interface YogaLearningDetail {
  title: string;
  summary: string;
  source: string;
  chartFact: string;
}

/** Yoga learning surface (Figma node 41:210). */
@Component({
  selector: 'as-yoga-learning-sheet',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SheetComponent],
  template: `
    <as-sheet (dismissed)="dismissed.emit()">
      <header class="head">
        <p class="eyebrow">LEARNING · YOGA</p>
        <h2>{{ detail().title }}</h2>
      </header>
      <p class="body">{{ detail().summary }}</p>
      <p class="eyebrow">CLASSICAL SOURCE</p>
      <div class="source">
        <p>{{ detail().source }}</p>
      </div>
      <p class="eyebrow">IN YOUR CHART</p>
      <p class="chart-fact">{{ detail().chartFact }}</p>
      <button class="got-it" type="button" (click)="dismissed.emit()">Got it</button>
    </as-sheet>
  `,
  styleUrl: './yoga-learning-sheet.component.scss',
})
export class YogaLearningSheetComponent {
  readonly detail = input.required<YogaLearningDetail>();
  readonly dismissed = output<void>();
}
