import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { SheetComponent } from '../sheet/sheet.component';

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
export class ListenSheetComponent {
  readonly title = input.required<string>();
  readonly subtitle = input('Daily guidance · gentle voice');
  /** Seconds. Placeholder timings until the synthesised track is wired. */
  readonly elapsed = input(12);
  readonly duration = input(32);
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
  readonly speed = input('1.0×');

  readonly dismissed = output<void>();
  readonly languageChanged = output<string>();

  protected readonly bars = WAVEFORM;

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

  protected readonly elapsedLabel = computed(() => this.clock(this.elapsed()));
  protected readonly remainingLabel = computed(
    () => `-${this.clock(Math.max(0, this.duration() - this.elapsed()))}`,
  );

  /** Transport state. The design specifies the paused frame; see the template. */
  readonly playing = signal(false);

  private clock(seconds: number): string {
    const whole = Math.floor(seconds);
    return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`;
  }
}
