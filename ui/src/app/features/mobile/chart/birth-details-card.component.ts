import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { VedicAll } from '../../../core/models';

/**
 * The reader's own birth constants — the panel every astrology app opens with,
 * and the one this app has never shown.
 *
 * It is not decoration. Birth data is how a reader checks the reading is even
 * about them: a wrong city or timezone makes every degree below it wrong, and
 * until now there was no way to notice. The same goes for ayanamsha — when two
 * apps disagree about someone's lagna it is almost always that, and we never
 * stated ours.
 *
 * Everything here already came back from `/vedic/{id}/avkahada`; the Reference
 * screen fetched `meta` and threw it away. No new request is made.
 */
export type BirthDetailsDensity = 'compact' | 'full';
export type BirthDetailsTone = 'plain' | 'guided';

interface Row { label: string; value: string; note?: string; }

@Component({
  selector: 'as-birth-details-card',
  standalone: true,
  templateUrl: './birth-details-card.component.html',
  styleUrl: './birth-details-card.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BirthDetailsCardComponent {
  readonly chart = input<VedicAll | null>(null);
  readonly personName = input<string | null>(null);
  readonly density = input<BirthDetailsDensity>('compact');
  /** Removes the nested card shell when this content lives inside a signature surface. */
  readonly embedded = input(false);
  /** `guided` names things the way a person would, not the way a chart does. */
  readonly tone = input<BirthDetailsTone>('plain');

  private readonly avk = computed<Record<string, unknown>>(
    () => (this.chart()?.avkahada ?? {}) as Record<string, unknown>,
  );

  private text(key: string): string | null {
    const value = this.avk()[key];
    return value === null || value === undefined || value === '' ? null : String(value);
  }

  protected readonly place = computed(() => this.chart()?.meta?.place ?? null);

  /** "15 May 1990 · 10:30 · Chennai" — one line a reader can sanity-check. */
  protected readonly born = computed(() => {
    const meta = this.chart()?.meta;
    if (!meta) return null;
    const date = new Date(`${meta.birth_date}T00:00:00`);
    const pretty = Number.isNaN(date.getTime())
      ? meta.birth_date
      : date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
    return [pretty, meta.birth_time, meta.place].filter(Boolean).join(' · ');
  });

  /** The three a person actually quotes about themselves. */
  protected readonly headline = computed<Row[]>(() => {
    const guided = this.tone() === 'guided';
    const nakshatra = this.text('nakshatra');
    const pada = this.text('charan');
    return [
      { label: guided ? 'Rising sign' : 'Lagna', value: this.text('lagna') ?? '—' },
      { label: guided ? 'Moon sign' : 'Rashi', value: this.text('rashi') ?? '—' },
      {
        // Pada as a separate note, not appended: "Pushya · pada 4" wrapped onto
        // a second line and made this column taller than the other two.
        label: guided ? 'Birth star' : 'Nakshatra',
        value: nakshatra ?? '—',
        note: nakshatra && pada ? `pada ${pada}` : undefined,
      },
    ];
  });

  /** Everything a practitioner expects to see stated, not assumed. */
  protected readonly placement = computed<Row[]>(() => {
    const meta = this.chart()?.meta;
    if (!meta) return [];
    const rows: Row[] = [];
    if (meta.place) rows.push({ label: 'Place', value: meta.place });
    if (meta.latitude !== undefined && meta.longitude !== undefined) {
      rows.push({
        label: 'Coordinates',
        value: `${meta.latitude.toFixed(4)}°, ${meta.longitude.toFixed(4)}°`,
      });
    }
    if (meta.timezone) rows.push({ label: 'Time zone', value: meta.timezone });
    if (meta.weekday) rows.push({ label: 'Weekday', value: meta.weekday });
    return rows;
  });

  /**
   * Stated because it is the usual reason two apps disagree about a lagna.
   * A reader comparing us with another app deserves to see which one we used.
   */
  protected readonly calculation = computed<Row[]>(() => {
    const meta = this.chart()?.meta;
    if (!meta) return [];
    const rows: Row[] = [];
    if (meta.ayanamsha?.name) {
      rows.push({
        label: 'Ayanamsha',
        value: meta.ayanamsha.dms ? `${meta.ayanamsha.name} · ${meta.ayanamsha.dms}` : meta.ayanamsha.name,
      });
    }
    if (meta.node_type) rows.push({ label: 'Nodes', value: `${meta.node_type} node` });
    if (meta.sidereal_time) rows.push({ label: 'Sidereal time', value: meta.sidereal_time });
    if (meta.local_mean_time) rows.push({ label: 'Local mean time', value: meta.local_mean_time });
    return rows;
  });

  protected readonly panchanga = computed<Row[]>(() =>
    ([['Tithi', 'tithi'], ['Yoga', 'yoga'], ['Karana', 'karana'], ['Paya', 'paya']] as const)
      .map(([label, key]) => ({ label, value: this.text(key) ?? '' }))
      .filter((row) => row.value !== ''),
  );

  protected readonly constants = computed<Row[]>(() =>
    ([['Varna', 'varna'], ['Vashya', 'vashya'], ['Yoni', 'yoni'], ['Gana', 'gana'],
      ['Nadi', 'nadi'], ['Tatwa', 'tatwa'], ['Vihaga', 'vihaga'],
      ['Name letter', 'name_letter']] as const)
      .map(([label, key]) => ({ label, value: this.text(key) ?? '' }))
      .filter((row) => row.value !== ''),
  );

  protected readonly lords = computed<Row[]>(() =>
    ([['Lagna lord', 'lagna_lord'], ['Rashi lord', 'rashi_lord'],
      ['Nakshatra lord', 'nakshatra_lord']] as const)
      .map(([label, key]) => ({ label, value: this.text(key) ?? '' }))
      .filter((row) => row.value !== ''),
  );

  protected readonly hasChart = computed(() => !!this.chart()?.meta);
}
