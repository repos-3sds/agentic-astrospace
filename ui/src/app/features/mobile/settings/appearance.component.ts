import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ThemePreference, ThemeService } from '../../../core/theme.service';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { SelectHapticDirective } from '../shared/select-haptic.directive';

interface AppearanceOption {
  id: ThemePreference;
  label: string;
  detail: string;
}

@Component({
  selector: 'as-appearance',
  standalone: true,
  imports: [BackLinkDirective, SelectHapticDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './appearance.component.html',
  styleUrl: './appearance.component.scss',
})
export class AppearanceComponent {
  protected readonly theme = inject(ThemeService);
  protected readonly options: AppearanceOption[] = [
    { id: 'system', label: 'System', detail: 'Follow your device setting' },
    { id: 'light', label: 'Light', detail: 'Warm and bright' },
    { id: 'dark', label: 'Dark', detail: 'Gentle in low light' },
  ];

  protected select(preference: ThemePreference): void {
    this.theme.setPreference(preference);
  }
}
