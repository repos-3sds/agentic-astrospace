import { ChangeDetectionStrategy, Component, output } from '@angular/core';
import { SheetComponent } from '../sheet/sheet.component';

/** Gajakesari learning surface (Figma node 41:210). */
@Component({
  selector: 'as-yoga-learning-sheet',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SheetComponent],
  template: `
    <as-sheet (dismissed)="dismissed.emit()">
      <header class="head">
        <p class="eyebrow">LEARNING · YOGA</p>
        <h2>Gajakesari Yoga</h2>
      </header>
      <p class="body">A yoga formed when the Moon and Jupiter share a kendra (a 1st, 4th, 7th, or 10th house relationship from each other) — classically linked to wisdom, good reputation, and steady judgement.</p>
      <p class="eyebrow">CLASSICAL SOURCE</p>
      <div class="source">
        <p>“Kendre Guruvyaya Chandre Gajakesaryakhyayogo...” — Moon and Jupiter in mutual kendra forms Gajakesari Yoga.</p>
        <p>Brihat Parashara Hora Shastra, ch. 36</p>
      </div>
      <p class="eyebrow">IN YOUR CHART</p>
      <p class="chart-fact">Your Moon is in Cancer (4th house) and Jupiter is in Taurus (1st house) — a kendra relationship, forming this yoga.</p>
      <button class="got-it" type="button" (click)="dismissed.emit()">Got it</button>
    </as-sheet>
  `,
  styleUrl: './yoga-learning-sheet.component.scss',
})
export class YogaLearningSheetComponent {
  readonly dismissed = output<void>();
}
