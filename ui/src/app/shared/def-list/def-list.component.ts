import { Component, input } from '@angular/core';
import { Tag } from 'primeng/tag';

export interface DefRow {
  label: string;
  value?: string | number | null;
  /** value pending reference-chart verification */
  unverified?: boolean;
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
