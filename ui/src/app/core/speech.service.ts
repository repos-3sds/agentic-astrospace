import { Injectable, signal } from '@angular/core';
import { Capacitor, PluginListenerHandle } from '@capacitor/core';
import { SpeechRecognition } from '@capacitor-community/speech-recognition';
import type { AskResponseLanguage } from './preferences.service';

/** BCP-47 tags the recognisers accept for each Ask response language. */
const RECOGNITION_LOCALES: Record<AskResponseLanguage, string> = { en: 'en-IN', te: 'te-IN' };

type BrowserRecognition = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
};

function browserRecognitionCtor(): (new () => BrowserRecognition) | null {
  if (typeof window === 'undefined') return null;
  const w = window as unknown as Record<string, unknown>;
  return (w['SpeechRecognition'] ?? w['webkitSpeechRecognition'] ?? null) as (new () => BrowserRecognition) | null;
}

/**
 * Speech-to-text for the Ask composer.
 *
 * The native app recognises through the platform engine via
 * `@capacitor-community/speech-recognition`; browsers that expose the Web
 * Speech API use that. Where neither exists `supported()` is false and the
 * composer hides its microphone rather than showing a button that does
 * nothing. Partial transcripts are published as they arrive so the reader can
 * see what was heard before confirming.
 */
@Injectable({ providedIn: 'root' })
export class SpeechService {
  readonly supported = signal(false);
  readonly listening = signal(false);
  readonly transcript = signal('');
  readonly error = signal<string | null>(null);

  private readonly native = Capacitor.isNativePlatform();
  private browser: BrowserRecognition | null = null;
  private nativeListeners: PluginListenerHandle[] = [];

  constructor() {
    if (this.native) {
      SpeechRecognition.available()
        .then(({ available }) => this.supported.set(available))
        .catch(() => this.supported.set(false));
    } else {
      this.supported.set(browserRecognitionCtor() !== null);
    }
  }

  /** Begins listening; resolves once the recogniser is running or has refused. */
  async start(language: AskResponseLanguage): Promise<void> {
    if (this.listening()) return;
    this.transcript.set('');
    this.error.set(null);
    const locale = RECOGNITION_LOCALES[language] ?? RECOGNITION_LOCALES.en;
    try {
      if (this.native) await this.startNative(locale);
      else this.startBrowser(locale);
      this.listening.set(true);
    } catch (error) {
      this.error.set(this.describe(error));
      this.listening.set(false);
    }
  }

  /** Stops listening and keeps whatever was heard in `transcript`. */
  async stop(): Promise<void> {
    if (this.native) {
      await SpeechRecognition.stop().catch(() => undefined);
      await this.dropNativeListeners();
    } else {
      this.browser?.stop();
      this.browser = null;
    }
    this.listening.set(false);
  }

  private async startNative(locale: string): Promise<void> {
    const permission = await SpeechRecognition.requestPermissions();
    if (permission.speechRecognition !== 'granted') {
      throw new Error('Microphone access is off for this app. Allow it in your phone settings to ask by voice.');
    }
    await this.dropNativeListeners();
    this.nativeListeners.push(
      await SpeechRecognition.addListener('partialResults', ({ matches }) => {
        if (matches?.[0]) this.transcript.set(matches[0]);
      }),
      await SpeechRecognition.addListener('listeningState', ({ status }) => {
        if (status === 'stopped') this.listening.set(false);
      }),
    );
    await SpeechRecognition.start({ language: locale, partialResults: true, popup: false, maxResults: 1 });
  }

  private startBrowser(locale: string): void {
    const Ctor = browserRecognitionCtor();
    if (!Ctor) throw new Error('Voice input is not available in this browser.');
    const recognition = new Ctor();
    recognition.lang = locale;
    recognition.interimResults = true;
    recognition.continuous = true;
    recognition.onresult = (event) => {
      let heard = '';
      for (let i = 0; i < event.results.length; i += 1) heard += event.results[i][0]?.transcript ?? '';
      this.transcript.set(heard.trim());
    };
    recognition.onerror = (event) => {
      if (event.error === 'aborted' || event.error === 'no-speech') return;
      this.error.set(
        event.error === 'not-allowed'
          ? 'Microphone access was refused. Allow it in your browser to ask by voice.'
          : 'Voice input stopped unexpectedly. You can keep typing instead.',
      );
    };
    recognition.onend = () => this.listening.set(false);
    recognition.start();
    this.browser = recognition;
  }

  private async dropNativeListeners(): Promise<void> {
    const handles = this.nativeListeners;
    this.nativeListeners = [];
    await Promise.all(handles.map((h) => h.remove().catch(() => undefined)));
  }

  private describe(error: unknown): string {
    const message = (error as Error | undefined)?.message;
    return message && message.length < 160 ? message : 'Voice input could not start. You can keep typing instead.';
  }
}
