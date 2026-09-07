import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Capacitor } from '@capacitor/core';
import { MobileTtsService } from '../../../core/mobile-tts.service';
import { AskResponseLanguage, PreferencesService } from '../../../core/preferences.service';
import { HapticsService } from '../../../core/haptics.service';

/** The languages the Ask agent can answer in. */
export type AppLanguage = AskResponseLanguage;

/** Text spoken when a voice row is tapped, so the choice is heard, not just read. */
const PREVIEW_TEXT =
  "Namaste. Here is your reading for today. The sky favours a steady, thoughtful pace.";

/**
 * Settings — Language & audio (Figma node 67:147).
 *
 * Language is a segmented control because there are two response languages,
 * and Telugu is written in Telugu. The app shell is still English; this
 * controls the language Siddha uses for generated Ask answers.
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

  readonly languages: { id: AppLanguage; label: string; detail: string }[] = [
    { id: 'en', label: 'English', detail: 'Natural Indian English' },
    { id: 'te', label: 'తెలుగు', detail: 'Simple Telugu with natural English words' },
  ];
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

  protected setLanguage(language: AppLanguage): void {
    this.haptics.select();
    this.preferences.language.set(language);
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
