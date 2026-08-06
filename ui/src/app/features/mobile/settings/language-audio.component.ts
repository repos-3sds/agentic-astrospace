import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Capacitor } from '@capacitor/core';
import { MobileTtsService } from '../../../core/mobile-tts.service';
import { PreferencesService } from '../../../core/preferences.service';
import { HapticsService } from '../../../core/haptics.service';

/** The languages the app reads and speaks in. */
export type AppLanguage = 'en' | 'te';

/** Text spoken when a voice row is tapped, so the choice is heard, not just read. */
const PREVIEW_TEXT =
  "Namaste. Here is your reading for today. The sky favours a steady, thoughtful pace.";

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
 *
 * Voice selection lists whatever the device's own TTS engine has installed —
 * see mobile-tts.service.ts's listVoices(). It cannot offer voices the device
 * doesn't have; the best it can do is let a reader pick the least robotic one
 * already there (and preview it before committing) instead of the app
 * silently guessing on their behalf.
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
  private readonly tts = inject(MobileTtsService);
  private readonly haptics = inject(HapticsService);
  protected readonly preferences = inject(PreferencesService);

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

  protected readonly nativeAvailable = Capacitor.isNativePlatform();
  protected readonly platform = Capacitor.getPlatform();
  protected readonly voicesLoading = signal(true);
  protected readonly voices = signal<{ name: string; lang: string }[]>([]);
  protected readonly previewing = signal<string | null>(null);

  constructor() {
    void this.loadVoices();
  }

  protected toggleReadAloud(): void {
    this.readAloud.update((on) => !on);
  }

  protected toggleGentleVoice(): void {
    this.gentleVoice.update((on) => !on);
  }

  protected isSelected(name: string | null): boolean {
    return this.preferences.voiceName() === name;
  }

  protected async chooseVoice(name: string | null): Promise<void> {
    this.haptics.select();
    await this.preview(name);
    this.preferences.voiceName.set(name);
  }

  protected openVoiceSettings(): void {
    this.haptics.tap();
    this.tts.openVoiceSettings();
  }

  protected voiceLabel(voice: { name: string; lang: string }): string {
    return voice.lang === 'en-IN' ? `${voice.name} · Indian English` : `${voice.name} · ${voice.lang}`;
  }

  protected voiceSettingsPath(): string {
    if (this.platform === 'android') {
      return 'Settings › Accessibility › Text-to-speech output';
    }
    if (this.platform === 'ios') {
      return 'Settings › Accessibility › Spoken Content › Voices';
    }
    return 'your phone’s voice settings';
  }

  private async loadVoices(): Promise<void> {
    this.voicesLoading.set(true);
    try {
      this.voices.set(await this.tts.listVoices());
    } finally {
      this.voicesLoading.set(false);
    }
  }

  /** Speaks a short sample through whichever voice was just selected. */
  private async preview(name: string | null): Promise<void> {
    this.previewing.set(name);
    try {
      await this.tts.stop();
      await this.tts.speak(PREVIEW_TEXT, { lang: 'en-IN', rate: 0.9, pitch: 0.96, voiceName: name });
    } finally {
      this.previewing.set(null);
    }
  }
}
