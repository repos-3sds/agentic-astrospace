import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'as-mobile-notes',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <header class="mnote-top"><a [routerLink]="['/m','chart']"><img src="mobile/back.svg" alt="" /><span>Your Chart</span></a><em>Local draft</em></header>
    <main class="mnote-body">
      <header><h1>Notes</h1><p>Local draft only. This is not synced to your AstroSpace account yet.</p></header>
      <textarea maxlength="2000" [value]="text()" (input)="update($event)" aria-label="Local draft notes" placeholder="Add a private draft for this session."></textarea>
      <div class="mnote-meta"><span>Draft not synced</span><span>{{ text().length }} / 2000</span></div>
      <p class="mnote-private">▢ <span>This draft stays local to this screen and may be cleared on reload. It is not sent to the reading engine.</span></p>
    </main>
  `,
  styleUrl: './notes.component.scss',
})
export class NotesComponent {
  readonly text = signal('');
  protected update(event: Event): void { this.text.set((event.target as HTMLTextAreaElement).value); }
}
