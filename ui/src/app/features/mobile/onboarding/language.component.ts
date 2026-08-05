import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { PreferencesService } from '../../../core/preferences.service';

@Component({
  selector: 'as-language',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './language.component.html',
  styleUrl: './language.component.scss',
  host: { class: 'as-mobile' },
})
export class LanguageComponent {
  private readonly preferences = inject(PreferencesService);

  // Only English actually works today (see the Telugu note in the template),
  // so this is the only value this signal can ever hold — but it still owns
  // the write-through to PreferencesService rather than letting the choice
  // evaporate on navigation.
  protected readonly language = signal<'English'>('English');

  constructor() {
    this.preferences.language.set('en');
  }
}
