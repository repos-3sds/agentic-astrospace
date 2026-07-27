import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

/** Which place the day's timings are computed for. */
export type TimingPlace = 'birth' | 'current';

/**
 * Settings — Location (Figma node 69:89).
 *
 * The footnote is the whole screen: the birth chart stays birth-based no matter
 * what is chosen here, and this only moves the daily panchang and windows.
 *
 * Without it the setting reads as "recompute my chart for where I am", which
 * would be wrong in a way people act on — a natal chart is fixed to the birth
 * moment and place, and nothing in an app should suggest it travels. What does
 * travel is sunrise, and with it Rahu Kalam, the tithi boundaries and every
 * muhurta window.
 */
@Component({
  selector: 'as-settings-location',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './location.component.html',
  styleUrl: './location.component.scss',
})
export class LocationComponent {
  readonly places: { id: TimingPlace; icon: string; label: string }[] = [
    { id: 'birth', icon: 'loc-birth', label: 'Birth place — Vijayawada' },
    { id: 'current', icon: 'loc-current', label: 'Current location' },
  ];

  readonly place = signal<TimingPlace>('birth');
}
