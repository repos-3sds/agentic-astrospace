import { Component, input } from '@angular/core';
import { LucideAngularModule } from 'lucide-angular';

@Component({
  selector: 'app-section-card',
  imports: [LucideAngularModule],
  templateUrl: './section-card.component.html',
  styleUrl: './section-card.component.scss',
})
export class SectionCardComponent {
  icon = input<string>();
  title = input.required<string>();
  subtitle = input<string>();
}
