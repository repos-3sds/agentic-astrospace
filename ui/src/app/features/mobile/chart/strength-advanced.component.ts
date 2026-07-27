import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

type StrengthTab = 'shadbala' | 'ashtakavarga' | 'jaimini';

interface PlanetStrength {
  name: string;
  score: number;
  virupa: number;
  minimum: number;
}

interface HouseBindu {
  house: string;
  sign: string;
  short: string;
  value: number;
  x: number;
  y: number;
}

/** Strength & Advanced complete tab flow (Figma 41:149, 60:88, 60:257). */
@Component({
  selector: 'as-strength-advanced',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './strength-advanced.component.html',
  styleUrl: './strength-advanced.component.scss',
})
export class StrengthAdvancedComponent {
  readonly tab = signal<StrengthTab>('shadbala');
  readonly avPlanet = signal('SAV');

  readonly strengths: PlanetStrength[] = [
    { name: 'Jupiter', score: 82, virupa: 420, minimum: 380 },
    { name: 'Moon', score: 68, virupa: 340, minimum: 360 },
    { name: 'Sun', score: 74, virupa: 365, minimum: 300 },
    { name: 'Saturn', score: 55, virupa: 275, minimum: 300 },
  ];

  readonly planets = ['SAV', 'Su', 'Mo', 'Ma', 'Me', 'Ju', 'Ve', 'Sa'];
  readonly houses: HouseBindu[] = [
    { house: '1st', sign: 'Taurus', short: 'Ta', value: 32, x: 50, y: 10 },
    { house: '2nd', sign: 'Gemini', short: 'Ge', value: 28, x: 79, y: 7 },
    { house: '3rd', sign: 'Cancer', short: 'Cn', value: 30, x: 93, y: 22 },
    { house: '4th', sign: 'Leo', short: 'Le', value: 26, x: 88, y: 50 },
    { house: '5th', sign: 'Virgo', short: 'Vi', value: 35, x: 93, y: 78 },
    { house: '6th', sign: 'Libra', short: 'Li', value: 24, x: 78, y: 93 },
    { house: '7th', sign: 'Scorpio', short: 'Sc', value: 33, x: 50, y: 88 },
    { house: '8th', sign: 'Sagittarius', short: 'Sg', value: 22, x: 22, y: 93 },
    { house: '9th', sign: 'Capricorn', short: 'Cp', value: 38, x: 7, y: 78 },
    { house: '10th', sign: 'Aquarius', short: 'Aq', value: 27, x: 12, y: 50 },
    { house: '11th', sign: 'Pisces', short: 'Pi', value: 36, x: 21, y: 7 },
    { house: '12th', sign: 'Aries', short: 'Ar', value: 25, x: 7, y: 21 },
  ];
  readonly displayedHouses = computed(() => {
    if (this.avPlanet() === 'SAV') return this.houses;
    const offset = this.planets.indexOf(this.avPlanet());
    return this.houses.map((house, index) => ({
      ...house,
      value: Math.max(2, Math.round((house.value + index + offset) / 5)),
    }));
  });
  readonly totalBindus = computed(() =>
    this.avPlanet() === 'SAV'
      ? 337
      : this.displayedHouses().reduce((total, house) => total + house.value, 0),
  );

  readonly karakas = [
    ['Atmakaraka', 'Saturn (self)', '27° 41’'],
    ['Amatyakaraka', 'Jupiter (career)', '24° 03’'],
    ['Bhratrikaraka', 'Mars (siblings)', '19° 55’'],
    ['Matrikaraka', 'Moon (mother)', '04° 51’'],
  ];
  readonly arudhas = [
    ['A1 · LAGNA', 'Leo'], ['A9', 'Aries'], ['A10', 'Gemini'], ['UPAPADA', 'Scorpio'],
  ];
  readonly specialLagnas = [
    ['Bhava Lagna', 'Body & circumstance', 'Gemini 18° 40′'],
    ['Hora Lagna', 'Wealth & resources', 'Leo 02° 15′'],
    ['Ghati Lagna', 'Power & position', 'Libra 11° 05′'],
  ];
}
