import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

const STORAGE_KEY = 'astrospace.mobile.notes.draft';

@Component({
  selector: 'as-mobile-notes',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <header class="mnote-top"><a [routerLink]="['/m','chart']"><img src="mobile/back.svg" alt="" /><span>Your Chart</span></a><em>Local draft</em></header>
    <main class="mnote-body">
      <header><h1>Notes</h1><p>Local draft only. This is not synced to your <span class="siddha-brand">Siddha</span> account yet.</p></header>
      <textarea
        maxlength="2000"
        [value]="text()"
        (input)="update($event)"
        aria-label="Local draft notes"
        placeholder="Add a private draft for this session."
        autocorrect="off"
        autocapitalize="off"
        autocomplete="off"
        spellcheck="false"
      ></textarea>
      <div class="mnote-meta"><span>Saved on this device</span><span>{{ text().length }} / 2000</span></div>
      <p class="mnote-private">▢ <span>This draft stays on this device only. It is not sent to the reading engine or your <span class="siddha-brand">Siddha</span> account.</span></p>
    </main>
  `,
  styleUrl: './notes.component.scss',
})
export class NotesComponent {
  readonly text = signal(localStorage.getItem(STORAGE_KEY) ?? '');
  protected update(event: Event): void {
    const value = (event.target as HTMLTextAreaElement).value;
    this.text.set(value);
    localStorage.setItem(STORAGE_KEY, value);
  }
}
