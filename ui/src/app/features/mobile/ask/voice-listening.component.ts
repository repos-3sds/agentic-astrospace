import { ChangeDetectionStrategy, Component, input, output, signal } from '@angular/core';

/**
 * Input-level meter bar heights, in px, as the design draws them.
 *
 * Unlike the Listen waveform these are not a position along a track — nothing
 * has been recorded yet — so they carry no meaning beyond "sound is arriving".
 */
const METER: readonly number[] = [
  6, 10, 16, 22, 14, 28, 20, 10, 24, 18, 12, 20, 26, 16, 10, 18, 22, 14, 8,
];

/**
 * Ask — Voice listening (Figma node 25:123).
 *
 * Full-bleed over everything including the tab bar: while the microphone is
 * open there is nothing else to do, and leaving navigation reachable invites a
 * tap that strands a live recording.
 *
 * The partial transcript is shown as it is recognised. Speech recognition
 * mishears names and place names constantly, and a reader who cannot see what
 * was heard has no way to know why the answer was about the wrong thing.
 */
@Component({
  selector: 'as-voice-listening',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './voice-listening.component.html',
  styleUrl: './voice-listening.component.scss',
})
export class VoiceListeningComponent {
  /** What has been recognised so far. Empty until the first words land. */
  readonly transcript = input('');
  readonly language = input('English');

  readonly cancelled = output<void>();
  readonly confirmed = output<string>();

  protected readonly meter = METER;
  protected readonly status = signal('Listening…');
}
