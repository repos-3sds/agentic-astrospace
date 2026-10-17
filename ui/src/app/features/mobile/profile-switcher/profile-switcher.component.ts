import { ChangeDetectionStrategy, Component, inject, output } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Kundli } from '../../../core/models';
import { KundliStore } from '../../../core/kundli.store';
import { SheetComponent } from '../sheet/sheet.component';
import { HapticsService } from '../../../core/haptics.service';
import { profileRelationLabel } from '../settings/profile-fields';

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
              <span>{{ relationLabel(profile.relation) }}</span>
            </span>
            @if (profile.id === kundlis.activeId()) {
              <span class="profile-check" aria-label="Active">✓</span>
            }
          </button>
        }
        <a class="profile-add" routerLink="/m/settings/profiles/new">
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
  protected readonly relationLabel = profileRelationLabel;
  readonly kundlis = inject(KundliStore);
  readonly dismissed = output<void>();
  private readonly haptics = inject(HapticsService);

  protected choose(profile: Kundli): void {
    // The switch is the committed action; re-choosing the active profile is not.
    if (profile.id !== this.kundlis.activeId()) this.haptics.success();
    this.kundlis.setActive(profile.id);
    this.dismissed.emit();
  }
}
