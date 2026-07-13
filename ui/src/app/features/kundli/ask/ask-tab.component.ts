import { AfterViewChecked, Component, ElementRef, computed, inject, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { LucideAngularModule } from 'lucide-angular';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';

import { AskService, TOOL_LABELS } from '../../../core/ask.service';
import { KundliStore } from '../../../core/kundli.store';
import { MarkdownPipe } from '../../../shared/markdown.pipe';
import { SectionCardComponent } from '../../../shared/section-card/section-card.component';

const SUGGESTIONS = [
  'What does my chart say about my career?',
  'When is a good time today to start something important?',
  'Am I in Sade Sati right now?',
  'What does my D9 say about marriage?',
];

@Component({
  selector: 'app-ask-tab',
  imports: [
    FormsModule,
    LucideAngularModule,
    ButtonModule,
    InputTextModule,
    MarkdownPipe,
    SectionCardComponent,
  ],
  templateUrl: './ask-tab.component.html',
  styleUrl: './ask-tab.component.scss',
})
export class AskTabComponent implements AfterViewChecked {
  private store = inject(KundliStore);
  protected readonly askSvc = inject(AskService);

  protected readonly suggestions = SUGGESTIONS;
  protected draft = '';

  private scroller = viewChild<ElementRef<HTMLElement>>('scroller');
  private lastCount = 0;

  protected readonly kundli = this.store.active;

  protected readonly messages = computed(() => {
    const id = this.store.activeId();
    return id ? this.askSvc.history(id)() : [];
  });

  protected toolLabel(tool: string): string {
    return TOOL_LABELS[tool] ?? tool;
  }

  protected send(question?: string): void {
    const id = this.store.activeId();
    const q = (question ?? this.draft).trim();
    if (!id || !q || this.askSvc.pending()) return;
    this.draft = '';
    this.askSvc.ask(id, q);
  }

  ngAfterViewChecked(): void {
    const count = this.messages().length + (this.askSvc.pending() ? 1 : 0);
    if (count !== this.lastCount) {
      this.lastCount = count;
      const el = this.scroller()?.nativeElement;
      if (el) el.scrollTop = el.scrollHeight;
    }
  }
}
