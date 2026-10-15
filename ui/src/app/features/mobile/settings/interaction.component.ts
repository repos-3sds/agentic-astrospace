import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { PreferencesService } from '../../../core/preferences.service';
import { HapticsService } from '../../../core/haptics.service';
import { BackLinkDirective } from '../../../core/back-link.directive';

@Component({
  selector: 'as-settings-interaction',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackLinkDirective],
  templateUrl: './interaction.component.html',
  styleUrl: './interaction.component.scss',
})
export class InteractionComponent {
  protected readonly preferences = inject(PreferencesService);
  private readonly haptics = inject(HapticsService);

  protected toggleHaptics(): void {
    this.preferences.hapticsEnabled.update((enabled) => !enabled);
    if (this.preferences.hapticsEnabled()) this.haptics.select();
  }
}
