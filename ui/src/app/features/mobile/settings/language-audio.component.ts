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
  /**
   * Telugu is listed but not selectable.
   *
   * The app has no UI translation, and `language` never reaches the agent — it
   * is stored on the message row and used to filter the remedies table, and
   * that is all. Offering the switch implied a translated app and Telugu
   * answers; it delivered neither.
   *
   * Shipping it for real means UI localisation, passing the language through to
   * generation, Telugu TTS for Listen, and extending the refer-out boundary,
   * which is English-only on both the input and output side. Until then this
   * says so rather than pretending.
   */
  readonly languages: { id: AppLanguage; label: string; ready: boolean }[] = [
    { id: 'en', label: 'English', ready: true },
    { id: 'te', label: 'తెలుగు', ready: false },
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
