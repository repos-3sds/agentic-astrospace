import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'as-mobile-notes',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <header class="mnote-top"><a [routerLink]="['/m','chart']"><img src="mobile/back.svg" alt="" /><span>Your Chart</span></a><em>✓&nbsp; Saved</em></header>
    <main class="mnote-body">
      <header><h1>Notes</h1><p>Private to you — never used in readings or shared.</p></header>
      <textarea maxlength="2000" [value]="text()" (input)="update($event)" aria-label="Private notes"></textarea>
      <div class="mnote-meta"><span>Last edited 2 days ago</span><span>{{ text().length }} / 2000</span></div>
      <p class="mnote-private">▢ <span>Stored privately on your account — not sent to the reading engine.</span></p>
    </main>
  `,
  styleUrl: './notes.component.scss',
})
export class NotesComponent {
  readonly text = signal('Amma’s astrologer in Vijayawada said the Saturn period would be heavy until 2028 — matches what the app shows.\n\nAsk about Aarav’s school admission timing when we next visit the temple.\n\nRemember: Venus–Saturn antar started Jan 2026.\n');
  protected update(event: Event): void { this.text.set((event.target as HTMLTextAreaElement).value); }
}
