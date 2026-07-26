import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

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
  protected readonly language = signal<'English' | 'Telugu'>('English');
}
