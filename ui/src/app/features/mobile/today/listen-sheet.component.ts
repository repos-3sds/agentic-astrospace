import {
  ChangeDetectionStrategy,
  Component,
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
  imports: [SheetComponent],
  templateUrl: './listen-sheet.component.html',
  styleUrl: './listen-sheet.component.scss',
})
export class ListenSheetComponent implements OnDestroy, OnInit {
  private readonly nativeTts = inject(MobileTtsService);

  readonly title = input.required<string>();
  readonly subtitle = input('Daily guidance · gentle voice');
  readonly script = input('');
  readonly sections = input<AudioReadingSection[]>([]);
  /**
   * Audio languages. Telugu is shown but not selectable — there is no Telugu
   * TTS and the reading itself is generated in English, so choosing it would
   * have changed nothing audible.
   */
  readonly languages = input<{ label: string; ready: boolean }[]>([
    { label: 'తెలుగు', ready: false },
    { label: 'English', ready: true },
  ]);
  readonly language = input('English');

  readonly dismissed = output<void>();
  readonly languageChanged = output<string>();

  protected readonly bars = WAVEFORM;
  protected readonly elapsed = signal(0);
  protected readonly speed = signal(0.9);
  protected readonly status = signal<string | null>(null);
  protected readonly chunkIndex = signal(0);

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
  protected readonly remainingLabel = computed(
    () => `-${this.clock(Math.max(0, this.duration() - this.elapsed()))}`,
  );
  protected readonly speedLabel = computed(() => `${this.speed().toFixed(1)}x`);
  protected readonly effectiveSections = computed<AudioReadingSection[]>(() => {
    const sections = this.sections().filter((section) => section.text.trim());
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
  protected readonly unsupported = computed(
    () =>
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

  ngOnInit(): void {
    void this.ensureVoices(false);
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
      if (this.nativeTts.nativeAvailable()) {
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
    if (!this.nativeTts.nativeAvailable() && window.speechSynthesis.paused && this.utterance) {
      window.speechSynthesis.resume();
      this.playing.set(true);
      this.startTimer();
      this.status.set(null);
      return;
    }
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

  private clock(seconds: number): string {
    const whole = Math.floor(seconds);
    return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`;
  }

  private chunks(): string[] {
    return this.chunksFor(this.scriptText());
  }

  private chunksFor(text: string): string[] {
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
    return (
      voices.find((voice) => PREFERRED_VOICE_NAMES.some((name) => voice.name.includes(name))) ??
      voices.find((voice) => voice.lang === lang) ??
      voices.find((voice) => voice.lang.startsWith('en')) ??
      null
    );
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
    return chunk
      .replace(/\bTarabala\b/g, 'Tara bala')
      .replace(/\bChandrabala\b/g, 'Chandra bala')
      .replace(/\bpanchang\b/gi, 'panchangam')
      .replace(/\bgochara\b/gi, 'gocharam')
      .replace(/\s+—\s+/g, ', ')
      .replace(/\s+/g, ' ')
      .trim();
  }
}
