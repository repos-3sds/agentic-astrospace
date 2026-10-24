import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { TextSizeChoice, TextSizeService } from '../../../core/text-size.service';
import { SelectHapticDirective } from '../shared/select-haptic.directive';

interface TextSizeOption {
  id: TextSizeChoice;
  label: string;
  detail: string;
}

/**
 * Settings > Text size: Siddha's own text size, apart from the phone's.
 * Testers on 360-wide phones with a large phone font saw every screen about
 * 1.3x the design (2026-10-24), so the phone's setting is followed only up to
 * 102%; a reader who wants larger text chooses it here. The whole screen
 * changes as soon as a size is picked, so the sample is the preview.
 */
@Component({
  selector: 'as-settings-text-size',
  standalone: true,
  imports: [BackLinkDirective, SelectHapticDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './text-size.component.html',
  styleUrl: './text-size.component.scss',
})
export class TextSizeComponent {
  protected readonly textSize = inject(TextSizeService);
  protected readonly options: TextSizeOption[] = [
    { id: 0, label: 'Same as phone', detail: 'Follows your phone, up to standard size' },
    { id: 90, label: 'Small', detail: 'More fits on each screen' },
    { id: 100, label: 'Standard', detail: 'As Siddha was designed' },
    { id: 115, label: 'Large', detail: 'Easier to read' },
    { id: 130, label: 'Extra large', detail: 'Easiest to read, longer screens' },
  ];

  constructor() {
    void this.textSize.load();
  }

  protected select(id: TextSizeChoice): void {
    void this.textSize.set(id);
  }
}
