import { ChangeDetectionStrategy, Component, inject, output } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Kundli } from '../../../core/models';
import { KundliStore } from '../../../core/kundli.store';
import { SheetComponent } from '../sheet/sheet.component';

@Component({
  selector: 'as-profile-switcher',
  standalone: true,
  imports: [RouterLink, SheetComponent],
  template: `
    <as-sheet (dismissed)="dismissed.emit()">
      <h2>Switch profile</h2>
      <div class="profile-list">
        @for (profile of kundlis.kundlis(); track profile.id) {
          <button
            type="button"
            class="profile-row"
            [class.is-active]="profile.id === kundlis.activeId()"
            (click)="choose(profile)"
          >
            <span class="profile-avatar">{{ profile.name.slice(0, 1).toUpperCase() }}</span>
            <span class="profile-copy">
              <strong>{{ profile.name }}</strong>
              <span>{{ profile.relation || 'Profile' }}</span>
            </span>
            @if (profile.id === kundlis.activeId()) {
              <span class="profile-check" aria-label="Active">✓</span>
            }
          </button>
        }
        <a class="profile-add" routerLink="/m/birth-details">
          <span class="profile-add-mark" aria-hidden="true">+</span>
          <strong>Add a profile</strong>
        </a>
      </div>
    </as-sheet>
  `,
  styleUrl: './profile-switcher.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProfileSwitcherComponent {
  readonly kundlis = inject(KundliStore);
  readonly dismissed = output<void>();
  readonly selected = output<Kundli>();

  protected choose(profile: Kundli): void {
    this.kundlis.setActive(profile.id);
    this.selected.emit(profile);
    this.dismissed.emit();
  }
}
