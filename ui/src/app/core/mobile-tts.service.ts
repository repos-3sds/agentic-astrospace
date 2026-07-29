import { Injectable } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import {
  QueueStrategy,
  SpeechSynthesisVoice,
  TextToSpeech,
} from '@capacitor-community/text-to-speech';

const PREFERRED_NATIVE_VOICES = [
  'Samantha',
  'Ava',
  'Allison',
  'Serena',
  'Daniel',
  'Karen',
  'Moira',
  'Rishi',
];

@Injectable({ providedIn: 'root' })
export class MobileTtsService {
  private voicesPromise: Promise<SpeechSynthesisVoice[]> | null = null;

  nativeAvailable(): boolean {
    return Capacitor.isNativePlatform();
  }

  async speak(text: string, options: { lang: string; rate: number; pitch: number }): Promise<void> {
    if (!this.nativeAvailable()) return;
    const voice = await this.bestVoiceIndex(options.lang);
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

  private async voices(): Promise<SpeechSynthesisVoice[]> {
    if (!this.voicesPromise) {
      this.voicesPromise = TextToSpeech.getSupportedVoices()
        .then((result) => result.voices ?? [])
        .catch(() => []);
    }
    return this.voicesPromise;
  }

  private async bestVoiceIndex(lang: string): Promise<{ index: number; lang: string } | null> {
    const voices = await this.voices();
    if (!voices.length) return null;
    const candidates = voices.map((voice, index) => ({ voice, index }));
    const preferred = candidates.find(({ voice }) =>
      PREFERRED_NATIVE_VOICES.some((name) => voice.name.includes(name)),
    );
    const exact = candidates.find(({ voice }) => voice.lang === lang);
    const english = candidates.find(({ voice }) => voice.lang.startsWith('en'));
    const selected = preferred ?? exact ?? english;
    return selected ? { index: selected.index, lang: selected.voice.lang } : null;
  }
}
