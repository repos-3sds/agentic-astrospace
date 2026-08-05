import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { PreferencesService } from '../../../core/preferences.service';
import { HapticsService } from '../../../core/haptics.service';

@Component({
  selector: 'as-settings-interaction',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
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
