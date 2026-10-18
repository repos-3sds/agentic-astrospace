import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  OnDestroy,
  OnInit,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { SheetComponent } from '../sheet/sheet.component';
import { AudioReadingSection } from './audio-reading-script';
import { MobileTtsService } from '../../../core/mobile-tts.service';
import { PreferencesService } from '../../../core/preferences.service';
import { NATURAL_VOICE_NAME, NaturalVoiceService, naturalChunks, prepareForSpeech } from '../../../core/natural-voice.service';
import { SelectHapticDirective } from '../shared/select-haptic.directive';
import { keepScreenAwakeWhile } from '../../../core/screen-awake';

/**
 * Natural voice is generated at 0.95x, which the sheet's default 0.9x setting
 * should play back unchanged; other speeds scale from there on the device.
 */
const TELUGU = 'తెలుగు';
const NATURAL_BASE_SPEED = 0.9;

/**
 * Bar heights of the waveform, in px, in the order the design draws them.
 *
 * Kept as literal design geometry rather than generated: a random or synthesised
 * envelope redraws itself on every change detection and the strip visibly
 * shimmers. Real audio replaces this with peaks from the decoded track.
 */
const WAVEFORM: readonly number[] = [
  8, 14, 20, 12, 26, 32, 22, 16, 30, 24, 18, 10,
  22, 34, 28, 20, 14, 24, 30, 18, 12, 26, 20, 16,
  28, 22, 12, 18, 10, 14, 20, 16, 10, 8,
];

const PREFERRED_VOICE_NAMES = [
  'Samantha',
  'Ava',
  'Allison',
  'Serena',
  'Daniel',
  'Karen',
  'Moira',
  'Rishi',
];

/**
 * Listen (Figma node 23:25) — the daily reading read aloud, per Epic B's
 * audio-first requirement.
 *
 * A sheet over Today rather than a screen of its own: the audio is the same
 * day's reading, and pushing a route would lose the reader's scroll position
 * for what is a transport control.
 *
 * Language and speed sit in the sheet, not in Settings, because the reason to
 * change either is almost always "not this voice, right now".
 */
@Component({
  selector: 'as-listen-sheet',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SheetComponent, SelectHapticDirective],
  templateUrl: './listen-sheet.component.html',
  styleUrl: './listen-sheet.component.scss',
})
export class ListenSheetComponent implements OnDestroy, OnInit {
  private readonly nativeTts = inject(MobileTtsService);
  private readonly naturalVoice = inject(NaturalVoiceService);
  private readonly preferences = inject(PreferencesService);

  readonly title = input.required<string>();
  readonly subtitle = input('Daily guidance · gentle voice');
  readonly script = input('');
  readonly sections = input<AudioReadingSection[]>([]);
  /** The language the parent last chose; Telugu is restored when it can be. */
  readonly language = input('English');

  readonly dismissed = output<void>();
  readonly languageChanged = output<string>();

  protected readonly bars = WAVEFORM;
  protected readonly elapsed = signal(0);
  protected readonly speed = signal(0.9);
  protected readonly status = signal<string | null>(null);
  protected readonly chunkIndex = signal(0);
  /**
   * 'natural' plays server-made audio (Plus); 'device' is the phone's own
   * voice. Starts as device and upgrades once the entitlement check returns,
   * so a slow network never delays the play button.
   */
  protected readonly mode = signal<'natural' | 'device'>('device');
  /**
   * Telugu needs natural voice (Chirp's te-IN voice) and a brief made of
   * sections the server can render in Telugu. The phone voice has no Telugu
   * voice it can be relied on for, and the Ask sheet's text is already in the
   * language it was answered in.
   */
  protected readonly chosen = signal<'en' | 'te'>('en');
  private readonly teluguSections = signal<AudioReadingSection[] | null>(null);
  protected readonly languages = computed(() => [
    { label: TELUGU, ready: this.mode() === 'natural' && this.sections().length > 0 },
    { label: 'English', ready: true },
  ]);
  protected readonly currentLanguage = computed(() => (this.chosen() === 'te' ? TELUGU : 'English'));
  protected readonly voiceLabel = computed(() =>
    this.mode() === 'natural' ? 'Natural voice' : 'Phone voice',
  );

  /**
   * How many bars are behind the playhead. Derived from the clock rather than
   * hardcoded so the strip and the timestamps can never disagree. Floored, not
   * rounded: a bar is only played once the playhead is past it, and rounding up
   * showed one bar more than the design at the design's own timings.
   */
  protected readonly playedBars = computed(() => {
    const fraction = this.duration() > 0 ? this.elapsed() / this.duration() : 0;
    return Math.floor(WAVEFORM.length * Math.min(1, Math.max(0, fraction)));
  });

  protected readonly duration = computed(() => {
    const words = this.scriptText().trim().split(/\s+/).filter(Boolean).length;
    return Math.max(12, Math.ceil(words / 2.35 / this.speed()));
  });
  protected readonly elapsedLabel = computed(() => this.clock(this.elapsed()));
  /**
   * Natural voice takes 9-16 s to make a new day's audio, and the sheet sat at
   * 0:00 with a play button, so it looked broken (regression 2026-10-17).
   * Every wait already sets a "Preparing…"/"Starting…" status; the play
   * button and the clock show it too.
   */
  protected readonly preparing = computed(() => /^(Preparing|Starting)/.test(this.status() ?? ''));
  protected readonly remainingLabel = computed(
    () => `-${this.clock(Math.max(0, this.duration() - this.elapsed()))}`,
  );
  protected readonly speedLabel = computed(() => `${this.speed().toFixed(1)}x`);
  protected readonly effectiveSections = computed<AudioReadingSection[]>(() => {
    const telugu = this.chosen() === 'te' ? this.teluguSections() : null;
    const sections = (telugu ?? this.sections()).filter((section) => section.text.trim());
    return sections.length ? sections : [{ label: 'Reading', text: this.script() }];
  });
  protected readonly scriptText = computed(() =>
    this.effectiveSections().map((section) => section.text).join(' '),
  );
  protected readonly activeSectionLabel = computed(() => {
    const starts = this.sectionStarts();
    const current = this.chunkIndex();
    return [...starts].reverse().find((section) => current >= section.index)?.label ?? 'Reading';
  });
  private readonly sectionStarts = computed(() => {
    let index = 0;
    return this.effectiveSections().map((section) => {
      const start = { label: section.label, index };
      index += this.chunksFor(section.text).length;
      return start;
    });
  });

  /** Transport state for browser/OS text-to-speech. */
  readonly playing = signal(false);

  constructor() {
    // A locked screen suspends the WebView and cuts the reading off mid-way.
    keepScreenAwakeWhile(this.playing, inject(DestroyRef));
  }
  protected readonly unsupported = computed(
    () =>
      this.mode() !== 'natural' &&
      !this.nativeTts.nativeAvailable() &&
      (typeof window === 'undefined' ||
        !('speechSynthesis' in window) ||
        typeof SpeechSynthesisUtterance === 'undefined'),
  );
  private utterance: SpeechSynthesisUtterance | null = null;
  private timer: ReturnType<typeof setInterval> | null = null;
  private startWatch: ReturnType<typeof setTimeout> | null = null;
  private nextSentenceTimer: ReturnType<typeof setTimeout> | null = null;
  private voicesReady: Promise<void> | null = null;
  private playbackRun = 0;
  private audio: HTMLAudioElement | null = null;
  /** Which chunk `audio` holds, so resume after a skip doesn't replay the old one. */
  private audioIndex = -1;

  /**
   * The entitlement check that picks the voice. Play waits briefly for it:
   * starting in the phone voice and switching on the next play was the bug
   * where the first tap read in the phone voice (2026-10-17).
   */
  private voiceDecision: Promise<void> | null = null;
  private voiceDecided = false;

  ngOnInit(): void {
    void this.ensureVoices(false);
    this.voiceDecision = this.naturalVoice.available().then((ok) => {
      this.voiceDecided = true;
      // A phone voice picked in Language & audio wins over the natural one.
      // Never switch voices under a reader who has already pressed play.
      if (ok && this.wantsNatural() && !this.playing() && this.chunkIndex() === 0) {
        this.mode.set('natural');
        if (this.language() === TELUGU && this.sections().length) {
          void this.chooseLanguage(TELUGU);
        } else {
          void this.naturalVoice.audioUrl(this.prepareForSpeech(this.chunks()[0] ?? '')).catch(() => undefined);
          this.prefetchTelugu();
        }
      }
    }, () => { this.voiceDecided = true; });
  }

  private wantsNatural(): boolean {
    const chosen = this.preferences.voiceName();
    return chosen === null || chosen === NATURAL_VOICE_NAME;
  }

  /**
   * Translate in the background and fetch the first Telugu piece, so the
   * Telugu switch doesn't wait on a model call and a synthesis in a row.
   */
  private prefetchTelugu(): void {
    const sections = this.sections().filter((section) => section.text.trim());
    if (!sections.length) return;
    void this.naturalVoice.telugu(sections).then((telugu) => {
      const first = naturalChunks(telugu.map((section) => section.text).join(' '))[0];
      if (first) void this.naturalVoice.audioUrl(this.prepareForSpeech(first)).catch(() => undefined);
    }, () => undefined);
  }

  ngOnDestroy(): void {
    this.stop();
  }

  protected toggle(): void {
    if (this.unsupported()) {
      this.status.set('Audio playback is not available in this browser.');
      return;
    }
    if (this.playing()) {
      if (this.mode() === 'natural') {
        // No playbackRun bump: the same run resumes, and its onended handler
        // must still advance to the next part.
        this.audio?.pause();
      } else if (this.nativeTts.nativeAvailable()) {
        this.playbackRun += 1;
        void this.nativeTts.stop();
      } else {
        window.speechSynthesis.pause();
      }
      this.playing.set(false);
      this.stopTimer();
      this.status.set('Paused.');
      return;
    }
    if (this.mode() === 'natural' && this.audio?.src && this.audio.paused && this.audio.currentTime > 0 && this.audioIndex === this.chunkIndex()) {
      const run = this.playbackRun;
      void this.audio.play().then(
        () => {
          if (run !== this.playbackRun) return;
          this.playing.set(true);
          this.startTimer();
          this.status.set(null);
        },
        () => {
          if (run === this.playbackRun) this.fallBackToDevice();
        },
      );
      return;
    }
    if (this.mode() === 'device' && !this.nativeTts.nativeAvailable() && window.speechSynthesis.paused && this.utterance) {
      window.speechSynthesis.resume();
      this.playing.set(true);
      this.startTimer();
      this.status.set(null);
      return;
    }
    if (!this.voiceDecided && this.mode() === 'device' && this.wantsNatural() && this.voiceDecision) {
      void this.startAfterVoiceDecision();
      return;
    }
    void this.speakFrom(this.chunkIndex());
  }

  /** Waits up to 3 s for the voice to be chosen, then plays in whichever it is. */
  private async startAfterVoiceDecision(): Promise<void> {
    this.status.set('Preparing natural voice...');
    await Promise.race([this.voiceDecision, new Promise((resolve) => setTimeout(resolve, 3000))]);
    this.voiceDecided = true;
    if (this.playing()) return;
    void this.speakFrom(this.chunkIndex());
  }

  protected skip(delta: number): void {
    const chunks = this.chunks();
    if (!chunks.length) return;
    const next = Math.min(chunks.length - 1, Math.max(0, this.chunkIndex() + delta));
    this.chunkIndex.set(next);
    this.elapsed.set(Math.floor(this.duration() * (next / chunks.length)));
    if (this.playing()) void this.speakFrom(next);
  }

  protected cycleSpeed(): void {
    const speeds = [0.8, 0.9, 1, 1.2];
    const next = speeds[(speeds.indexOf(this.speed()) + 1) % speeds.length];
    this.speed.set(next);
    if (this.mode() === 'natural') {
      if (this.audio) this.audio.playbackRate = next / NATURAL_BASE_SPEED;
      return;
    }
    if (this.playing()) void this.speakFrom(this.chunkIndex());
  }

  protected jumpToSection(label: string): void {
    const start = this.sectionStarts().find((section) => section.label === label);
    if (!start) return;
    this.chunkIndex.set(start.index);
    this.elapsed.set(Math.floor(this.duration() * (start.index / Math.max(1, this.chunks().length))));
    this.status.set(`Ready: ${label}.`);
    if (this.playing()) void this.speakFrom(start.index);
  }

  protected async chooseLanguage(label: string): Promise<void> {
    const wanted = label === TELUGU ? 'te' : 'en';
    if (wanted === this.chosen() && (wanted === 'en' || this.teluguSections())) return;
    this.resetForSwitch();
    if (wanted === 'en') {
      this.chosen.set('en');
      this.status.set(null);
      this.languageChanged.emit('English');
      return;
    }
    this.status.set('Preparing Telugu...');
    try {
      const sections = await this.naturalVoice.telugu(this.sections().filter((section) => section.text.trim()));
      // Both used to return with "Preparing Telugu..." still showing, so the
      // switch looked like it quietly reverted (regression 2026-10-17, M4).
      if (this.mode() !== 'natural') {
        this.status.set('Telugu needs the natural voice, which isn’t available right now; staying in English.');
        return;
      }
      if (this.playing()) {
        this.status.set('Playing in English. Pause, then choose Telugu again to switch.');
        return;
      }
      this.teluguSections.set(sections);
      this.chosen.set('te');
      this.status.set('Ready in Telugu.');
      this.languageChanged.emit(TELUGU);
      void this.naturalVoice.audioUrl(this.prepareForSpeech(this.chunks()[0] ?? '')).catch(() => undefined);
    } catch {
      this.status.set('Telugu is unavailable right now; staying in English.');
    }
  }

  private resetForSwitch(): void {
    this.stop();
    this.playing.set(false);
    this.chunkIndex.set(0);
    this.elapsed.set(0);
    this.audioIndex = -1;
  }

  private clock(seconds: number): string {
    const whole = Math.floor(seconds);
    return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`;
  }

  private chunks(): string[] {
    return this.chunksFor(this.scriptText());
  }

  /**
   * Natural voice and the phone's native voice read a whole section at a
   * time: one utterance per sentence restarts the intonation and leaves a gap
   * at every full stop, which is most of what made read-aloud sound robotic.
   * Only the browser's speechSynthesis keeps sentence chunks, because Chrome
   * silently cuts off long utterances after about fifteen seconds.
   */
  private chunksFor(text: string): string[] {
    if (this.mode() === 'natural' || this.nativeTts.nativeAvailable()) {
      return naturalChunks(text);
    }
    return text
      .split(/(?<=[.!?])\s+/)
      .map((chunk) => chunk.trim())
      .filter(Boolean);
  }

  private speakFrom(index: number): void {
    if (this.unsupported()) {
      this.status.set('Audio playback is not available in this browser.');
      return;
    }
    const chunks = this.chunks();
    if (!chunks.length) {
      this.status.set('Nothing to read yet.');
      return;
    }
    this.clearStartWatch();
    this.clearNextSentenceTimer();
    if (this.mode() === 'natural') {
      void this.speakNaturalFrom(index, chunks);
      return;
    }
    if (this.nativeTts.nativeAvailable()) {
      void this.speakNativeFrom(index, chunks);
      return;
    }
    void this.ensureVoices(false);
    window.speechSynthesis.cancel();
    this.chunkIndex.set(index);
    this.playing.set(false);
    this.status.set('Starting audio...');
    const utterance = new SpeechSynthesisUtterance(this.prepareForSpeech(chunks[index]));
    utterance.lang = this.language() === 'English' ? 'en-US' : 'en';
    utterance.rate = this.speed();
    utterance.pitch = 0.96;
    utterance.volume = 1;
    utterance.voice = this.voiceFor(utterance.lang);
    utterance.onstart = () => {
      if (this.utterance !== utterance) return;
      this.clearStartWatch();
      this.playing.set(true);
      this.status.set(null);
      this.startTimer();
    };
    utterance.onend = () => {
      if (this.utterance !== utterance) return;
      this.clearStartWatch();
      const next = index + 1;
      if (next < chunks.length) {
        this.chunkIndex.set(next);
        this.elapsed.set(Math.floor(this.duration() * (next / chunks.length)));
        this.nextSentenceTimer = setTimeout(() => {
          if (this.playing()) this.speakFrom(next);
        }, this.pauseAfter(chunks[index]));
        return;
      }
      this.finishPlayback();
    };
    utterance.onerror = () => {
      if (this.utterance !== utterance) return;
      this.clearStartWatch();
      this.clearNextSentenceTimer();
      this.playing.set(false);
      this.status.set('Could not start audio. Check mute/volume, then try again.');
      this.stopTimer();
    };
    this.utterance = utterance;
    window.speechSynthesis.speak(utterance);
    window.speechSynthesis.resume();
    this.startWatch = setTimeout(() => {
      if (this.utterance !== utterance) return;
      if (window.speechSynthesis.speaking || window.speechSynthesis.pending) {
        this.playing.set(true);
        this.status.set(null);
        this.startTimer();
        return;
      }
      this.playing.set(false);
      this.status.set('Audio did not start. Check mute/volume, then try again.');
      this.stopTimer();
    }, 900);
  }

  private voiceFor(lang: string): SpeechSynthesisVoice | null {
    const voices = window.speechSynthesis.getVoices();
    const chosenName = this.preferences.voiceName();
    const chosen = chosenName ? voices.find((voice) => voice.name === chosenName) : undefined;
    return (
      chosen ??
      voices.find((voice) => PREFERRED_VOICE_NAMES.some((name) => voice.name.includes(name))) ??
      voices.find((voice) => voice.lang === lang) ??
      voices.find((voice) => voice.lang.startsWith('en')) ??
      null
    );
  }

  private async speakNaturalFrom(index: number, chunks: string[]): Promise<void> {
    const run = ++this.playbackRun;
    this.chunkIndex.set(index);
    this.audio?.pause();
    this.stopTimer();
    this.status.set('Preparing natural voice...');
    let url: string;
    try {
      url = await this.naturalVoice.audioUrl(this.prepareForSpeech(chunks[index]));
    } catch {
      if (run === this.playbackRun) this.fallBackToDevice();
      return;
    }
    if (run !== this.playbackRun) return;
    const audio = this.audio ?? (this.audio = new Audio());
    audio.onended = () => {
      if (run !== this.playbackRun) return;
      const next = index + 1;
      if (next < chunks.length) {
        this.elapsed.set(Math.floor(this.duration() * (next / chunks.length)));
        void this.speakNaturalFrom(next, chunks);
        return;
      }
      this.finishPlayback();
    };
    audio.onerror = () => {
      if (run === this.playbackRun) this.fallBackToDevice();
    };
    audio.src = url;
    this.audioIndex = index;
    audio.playbackRate = this.speed() / NATURAL_BASE_SPEED;
    try {
      await audio.play();
    } catch {
      if (run === this.playbackRun) this.fallBackToDevice();
      return;
    }
    if (run !== this.playbackRun) return;
    this.playing.set(true);
    this.status.set(null);
    this.startTimer();
    // Fetch the next part while this one plays, so sections join without a wait.
    const following = chunks[index + 1];
    if (following) {
      void this.naturalVoice.audioUrl(this.prepareForSpeech(following)).catch(() => undefined);
    }
  }

  /** Natural voice failed (offline, provider down): carry on with the phone voice. */
  private fallBackToDevice(): void {
    const label = this.activeSectionLabel();
    this.audio?.pause();
    this.mode.set('device');
    if (this.chosen() === 'te') {
      // The phone voice can't read the Telugu text well; go back to English.
      this.chosen.set('en');
      this.languageChanged.emit('English');
    }
    const start = this.sectionStarts().find((section) => section.label === label)?.index ?? 0;
    this.status.set('Natural voice is unavailable right now; using the phone voice.');
    if (this.unsupported()) {
      this.playing.set(false);
      this.stopTimer();
      return;
    }
    this.speakFrom(start);
  }

  private async speakNativeFrom(index: number, chunks: string[]): Promise<void> {
    const run = ++this.playbackRun;
    this.chunkIndex.set(index);
    this.playing.set(true);
    this.status.set('Playing through device voice.');
    this.startTimer();
    try {
      await this.nativeTts.stop();
      await this.nativeTts.speak(this.prepareForSpeech(chunks[index]), {
        lang: this.language() === 'English' ? 'en-US' : 'en',
        rate: this.speed(),
        pitch: 0.96,
      });
      if (run !== this.playbackRun) return;
      const next = index + 1;
      if (next < chunks.length) {
        this.chunkIndex.set(next);
        this.elapsed.set(Math.floor(this.duration() * (next / chunks.length)));
        this.nextSentenceTimer = setTimeout(() => {
          if (this.playing()) void this.speakNativeFrom(next, chunks);
        }, this.pauseAfter(chunks[index]));
        return;
      }
      this.finishPlayback();
    } catch {
      if (run !== this.playbackRun) return;
      this.playing.set(false);
      this.status.set('Could not start device audio. Check system TTS settings, then try again.');
      this.stopTimer();
    }
  }

  private ensureVoices(showStatus = true): Promise<void> {
    if (this.nativeTts.nativeAvailable()) return Promise.resolve();
    if (this.unsupported()) return Promise.resolve();
    if (window.speechSynthesis.getVoices().length) return Promise.resolve();
    if (this.voicesReady) return this.voicesReady;
    if (showStatus) this.status.set('Preparing voice...');
    this.voicesReady = new Promise((resolve) => {
      const finish = () => {
        window.speechSynthesis.onvoiceschanged = null;
        resolve();
      };
      window.speechSynthesis.onvoiceschanged = finish;
      setTimeout(finish, 800);
    });
    return this.voicesReady;
  }

  private startTimer(): void {
    this.stopTimer();
    this.timer = setInterval(() => {
      this.elapsed.update((value) => Math.min(this.duration(), value + 1));
    }, 1000);
  }

  private stopTimer(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
  }

  private stop(): void {
    this.playbackRun += 1;
    this.clearStartWatch();
    this.clearNextSentenceTimer();
    this.stopTimer();
    if (this.audio) {
      this.audio.onended = null;
      this.audio.onerror = null;
      this.audio.pause();
      this.audio = null;
    }
    void this.nativeTts.stop();
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  }

  private clearStartWatch(): void {
    if (this.startWatch) clearTimeout(this.startWatch);
    this.startWatch = null;
  }

  private clearNextSentenceTimer(): void {
    if (this.nextSentenceTimer) clearTimeout(this.nextSentenceTimer);
    this.nextSentenceTimer = null;
  }

  private finishPlayback(): void {
    this.clearNextSentenceTimer();
    this.playing.set(false);
    this.elapsed.set(this.duration());
    this.chunkIndex.set(0);
    this.stopTimer();
  }

  private pauseAfter(chunk: string): number {
    if (/^(Namaste|Here is|Take the day|Move with attention)/i.test(chunk)) return 650;
    if (/[;:]$/.test(chunk)) return 520;
    return 380;
  }

  private prepareForSpeech(chunk: string): string {
    return prepareForSpeech(chunk);
  }
}
