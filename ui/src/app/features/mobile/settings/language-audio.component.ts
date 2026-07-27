import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

/** The languages the app reads and speaks in. */
export type AppLanguage = 'en' | 'te';

/**
 * Settings — Language & audio (Figma node 67:147).
 *
 * Language is a segmented control rather than a list because there are two of
 * them, and Telugu is written in Telugu. A language picker that names languages
 * only in English is useless to the person most likely to need it.
 *
 * Both switches describe their consequence rather than their mechanism —
 * "Adds a Listen button to your daily card", not "Enable TTS". Someone turning
 * audio off should be able to tell what will disappear.
 */
@Component({
  selector: 'as-settings-language-audio',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './language-audio.component.html',
  styleUrl: './language-audio.component.scss',
})
export class LanguageAudioComponent {
  readonly languages: { id: AppLanguage; label: string }[] = [
    { id: 'en', label: 'English' },
    { id: 'te', label: 'తెలుగు' },
  ];

  readonly language = signal<AppLanguage>('en');
  readonly readAloud = signal(true);
  readonly gentleVoice = signal(true);

  protected toggleReadAloud(): void {
    this.readAloud.update((on) => !on);
  }

  protected toggleGentleVoice(): void {
    this.gentleVoice.update((on) => !on);
  }
}
