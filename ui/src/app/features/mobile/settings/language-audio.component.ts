import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Capacitor } from '@capacitor/core';
import { MobileTtsService } from '../../../core/mobile-tts.service';
import { NATURAL_VOICE_NAME, NaturalVoiceService } from '../../../core/natural-voice.service';
import { AskResponseLanguage, PreferencesService } from '../../../core/preferences.service';
import { HapticsService } from '../../../core/haptics.service';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { StickyBarDirective } from '../shared/sticky-bar.directive';

/** The languages the Ask agent can answer in. */
export type AppLanguage = AskResponseLanguage;

/** Text spoken when a voice row is tapped, so the choice is heard, not just read. */
const PREVIEW_TEXT =
  "Namaste. Here is your reading for today. The sky favours a steady, thoughtful pace.";

/**
 * Settings — Language & audio (Figma node 67:147).
 *
 * Language uses the same cards as onboarding's language step, and Telugu is
 * written in Telugu. The app shell is still English; this controls the
 * language Siddha uses for generated Ask answers.
 *
 * The read-aloud switch describes its consequence rather than its mechanism
 * ("Shows a Listen button on your daily card", not "Enable TTS"), and Today
 * honours it, so someone turning audio off can tell what will disappear.
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
  imports: [StickyBarDirective, BackLinkDirective],
  templateUrl: './language-audio.component.html',
  styleUrl: './language-audio.component.scss',
})
export class LanguageAudioComponent {
  private readonly tts = inject(MobileTtsService);
  private readonly haptics = inject(HapticsService);
  private readonly naturalVoice = inject(NaturalVoiceService);
  private readonly router = inject(Router);
  protected readonly preferences = inject(PreferencesService);

  /**
   * "Automatic" (null) means the natural voice when the plan has it. Once it
   * does, the phone's own automatic voice needs a name of its own: an empty
   * one, which the Listen sheet treats as automatic without the natural voice.
   */
  protected readonly PHONE_AUTO = '';
  /** Whether the plan includes Siddha's natural voice; null while checking. */
  protected readonly naturalAvailable = signal<boolean | null>(null);
  private sampleAudio: HTMLAudioElement | null = null;

  readonly languages: { id: AppLanguage; label: string; detail: string }[] = [
    { id: 'en', label: 'English', detail: 'Natural Indian English' },
    { id: 'te', label: 'తెలుగు', detail: 'Simple Telugu with natural English words' },
  ];
  readonly readAloud = this.preferences.readAloud;

  protected readonly nativeAvailable = Capacitor.isNativePlatform();
  protected readonly platform = Capacitor.getPlatform();
  protected readonly voicesLoading = signal(true);
  protected readonly voices = signal<{ name: string; lang: string }[]>([]);
  protected readonly previewing = signal<string | null>(null);

  constructor() {
    void this.loadVoices();
    void this.naturalVoice.available().then((ok) => this.naturalAvailable.set(ok));
  }

  /**
   * Siddha's natural voice comes with Plus. With it, choosing the row plays a
   * sample in that voice; without it, the row opens Plans.
   */
  protected async chooseNatural(): Promise<void> {
    this.haptics.select();
    if (!this.naturalAvailable()) {
      void this.router.navigate(['/m', 'subscription'], { queryParams: { from: 'audio.natural_voice', plan: 'plus' } });
      return;
    }
    this.preferences.voiceName.set(NATURAL_VOICE_NAME);
    this.previewing.set(NATURAL_VOICE_NAME);
    try {
      await this.tts.stop();
      this.sampleAudio?.pause();
      this.sampleAudio = new Audio(await this.naturalVoice.audioUrl(PREVIEW_TEXT));
      await this.sampleAudio.play();
    } catch {
      // The choice is saved even if the sample can't play (offline, muted).
    } finally {
      this.previewing.set(null);
    }
  }

  protected phoneAutoSelected(): boolean {
    const name = this.preferences.voiceName();
    return !this.naturalSelected() && (name === null || name === this.PHONE_AUTO);
  }

  /** Automatic means the natural voice when the plan has it. */
  protected naturalSelected(): boolean {
    const name = this.preferences.voiceName();
    return !!this.naturalAvailable() && (name === NATURAL_VOICE_NAME || name === null);
  }

  protected toggleReadAloud(): void {
    this.haptics.select();
    this.readAloud.update((on) => !on);
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
    this.sampleAudio?.pause();
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
