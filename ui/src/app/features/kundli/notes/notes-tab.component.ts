import { Component, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { LucideAngularModule } from 'lucide-angular';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { TextareaModule } from 'primeng/textarea';

import { KundliStore } from '../../../core/kundli.store';
import { SectionCardComponent } from '../../../shared/section-card/section-card.component';

@Component({
  selector: 'app-notes-tab',
  imports: [FormsModule, LucideAngularModule, ButtonModule, TextareaModule, SectionCardComponent],
  templateUrl: './notes-tab.component.html',
  styleUrl: './notes-tab.component.scss',
})
export class NotesTabComponent {
  private store = inject(KundliStore);
  private messages = inject(MessageService);

  protected readonly kundli = this.store.active;
  protected readonly saving = signal(false);
  protected notes = '';

  constructor() {
    effect(() => {
      this.notes = this.store.active()?.notes ?? '';
    });
  }

  protected async save(): Promise<void> {
    const active = this.store.active();
    if (!active) return;
    this.saving.set(true);
    try {
      await this.store.update(active.id, { notes: this.notes });
      this.messages.add({ severity: 'success', summary: 'Notes saved' });
    } catch (e) {
      this.messages.add({
        severity: 'error',
        summary: 'Save failed',
        detail: (e as Error).message,
      });
    } finally {
      this.saving.set(false);
    }
  }
}
