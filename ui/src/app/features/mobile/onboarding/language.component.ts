import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AskResponseLanguage, PreferencesService } from '../../../core/preferences.service';
import { BackLinkDirective } from '../../../core/back-link.directive';

@Component({
  selector: 'as-language',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackLinkDirective, RouterLink],
  templateUrl: './language.component.html',
  styleUrl: './language.component.scss',
  host: { class: 'as-mobile' },
})
export class LanguageComponent {
  private readonly preferences = inject(PreferencesService);

  /** The same two Ask response languages Settings offers (`language-audio`);
   * both screens write the one preference so the choice survives setup. */
  protected readonly language = this.preferences.language;

  protected choose(language: AskResponseLanguage): void {
    this.preferences.language.set(language);
  }
}
