import { Injectable, inject } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import {
  QueueStrategy,
  SpeechSynthesisVoice,
  TextToSpeech,
} from '@capacitor-community/text-to-speech';
import { PreferencesService } from './preferences.service';

/**
 * Fallback ranking when the user hasn't picked a voice (Settings → Language
 * & audio → Voice). "Rishi" is the closest built-in Indian-English voice on
 * iOS/Android, but it — like every name here — is whatever the device
 * happens to have installed at its default quality tier; a user-selected
 * voice from `listVoices()` always wins over this list.
 */
const PREFERRED_NATIVE_VOICES = [
  'Rishi',
  'Samantha',
  'Ava',
  'Allison',
  'Serena',
  'Daniel',
  'Karen',
  'Moira',
];

@Injectable({ providedIn: 'root' })
export class MobileTtsService {
  private readonly preferences = inject(PreferencesService);
  private voicesPromise: Promise<SpeechSynthesisVoice[]> | null = null;

  nativeAvailable(): boolean {
    return Capacitor.isNativePlatform();
  }

  async speak(
    text: string,
    options: { lang: string; rate: number; pitch: number; voiceName?: string | null },
  ): Promise<void> {
    if (!this.nativeAvailable()) return;
    const voice = await this.bestVoiceIndex(options.lang, options.voiceName);
    await TextToSpeech.speak({
      text,
      lang: voice?.lang ?? options.lang,
      rate: options.rate,
      pitch: options.pitch,
      volume: 1,
      voice: voice?.index,
      category: 'playback',
      queueStrategy: QueueStrategy.Flush,
    });
  }

  async stop(): Promise<void> {
    if (!this.nativeAvailable()) return;
    await TextToSpeech.stop();
  }

  /**
   * Jumps to the OS's own voice settings, where a reader can download a
   * higher-quality voice this app can then pick up via listVoices().
   *
   * Neither platform offers a public deep link straight into the exact
   * screen ("Spoken Content › Voices" on iOS, buried under Accessibility on
   * Android): Android has a documented intent action for its system TTS
   * settings, but iOS only allows jumping into the Settings app itself, not
   * past its own page — Apple has no public API for going deeper. The
   * on-screen instructions next to this button are load-bearing, not
   * decorative, because of that gap.
   */
  openVoiceSettings(): void {
    if (!this.nativeAvailable()) return;
    // window.open(url, '_system') is the standard Capacitor/Cordova idiom for
    // handing a custom URL scheme to the OS — there's no dedicated plugin API
    // for it, and @capacitor/app has no openUrl method (only appUrlOpen, for
    // receiving links, not sending them).
    const url =
      Capacitor.getPlatform() === 'android'
        ? 'intent:#Intent;action=android.settings.TTS_SETTINGS;end'
        : 'app-settings:';
    try {
      window.open(url, '_system');
    } catch {
      // Best-effort only — the written steps beside the button still stand.
    }
  }

  /** Voices installed on this device, for the Settings picker. Empty on web. */
  async listVoices(): Promise<{ name: string; lang: string }[]> {
    if (!this.nativeAvailable()) return [];
    const voices = await this.voices();
    return voices
      .filter((voice) => voice.lang.startsWith('en'))
      .map((voice) => ({ name: voice.name, lang: voice.lang }))
      .sort((a, b) => {
        const aIndia = a.lang === 'en-IN' ? 0 : 1;
        const bIndia = b.lang === 'en-IN' ? 0 : 1;
        return aIndia - bIndia || a.name.localeCompare(b.name);
      });
  }

  private async voices(): Promise<SpeechSynthesisVoice[]> {
    if (!this.voicesPromise) {
      this.voicesPromise = TextToSpeech.getSupportedVoices()
        .then((result) => result.voices ?? [])
        .catch(() => []);
    }
    return this.voicesPromise;
  }

  private async bestVoiceIndex(lang: string, voiceName = this.preferences.voiceName()): Promise<{ index: number; lang: string } | null> {
    const voices = await this.voices();
    if (!voices.length) return null;
    const candidates = voices.map((voice, index) => ({ voice, index }));

    const chosen = voiceName ? candidates.find(({ voice }) => voice.name === voiceName) : undefined;
    if (chosen) return { index: chosen.index, lang: chosen.voice.lang };

    // The saved voice no longer exists on this device (OS update, different
    // device) — fall through to the same auto-pick a user who never chose
    // one gets, rather than silently going mute.
    const preferred = candidates.find(({ voice }) =>
      PREFERRED_NATIVE_VOICES.some((name) => voice.name.includes(name)),
    );
    const exact = candidates.find(({ voice }) => voice.lang === lang);
    const english = candidates.find(({ voice }) => voice.lang.startsWith('en'));
    const selected = preferred ?? exact ?? english;
    return selected ? { index: selected.index, lang: selected.voice.lang } : null;
  }
}
