import { Component, input } from '@angular/core';
import { Tag } from 'primeng/tag';

export interface DefRow {
  label: string;
  value?: string | number | null;
  /** value pending reference-chart verification */
  unverified?: boolean;
  /** hex colour rendered as a small swatch dot before the value */
  swatch?: string;
  /** secondary muted line under the value (e.g. a source/explanation) */
  hint?: string;
}

@Component({
  selector: 'app-def-list',
  imports: [Tag],
  templateUrl: './def-list.component.html',
  styleUrl: './def-list.component.scss',
})
export class DefListComponent {
  rows = input.required<DefRow[]>();
}
