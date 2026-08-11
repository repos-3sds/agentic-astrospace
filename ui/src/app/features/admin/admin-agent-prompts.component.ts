import { Component, computed, inject, input, signal } from '@angular/core';
import { LucideAngularModule } from 'lucide-angular';
import { MessageService } from 'primeng/api';

import { AgentPromptRegistry } from '../../core/admin.service';

@Component({
  selector: 'app-admin-agent-prompts',
  imports: [LucideAngularModule],
  templateUrl: './admin-agent-prompts.component.html',
  styleUrl: './admin-agent-prompts.component.scss',
})
export class AdminAgentPromptsComponent {
  private messages = inject(MessageService);

  readonly registry = input.required<AgentPromptRegistry>();
  protected readonly selectedKey = signal('base');
  protected readonly selectedPrompt = computed(() => {
    const registry = this.registry();
    if (this.selectedKey() === 'base') {
      return {
        name: registry.base.name,
        description: 'Shared by every configured specialist. Runtime context is inserted server-side.',
        sourceFile: registry.base.source_file,
        symbol: registry.base.symbol,
        body: registry.base.prompt,
        kind: 'shared',
      };
    }
    const domain = registry.domains.find((item) => item.id === this.selectedKey());
    return domain ? {
      name: domain.name,
      description: domain.description,
      sourceFile: domain.source_file,
      symbol: domain.symbol,
      body: domain.addendum,
      kind: 'addendum',
    } : null;
  });

  protected selectPrompt(key: string): void {
    this.selectedKey.set(key);
  }

  protected async copyPrompt(): Promise<void> {
    const prompt = this.selectedPrompt();
    if (!prompt) return;
    try {
      await navigator.clipboard.writeText(prompt.body);
      this.messages.add({
        severity: 'success',
        summary: 'Prompt copied',
        detail: `${prompt.name} is on your clipboard.`,
      });
    } catch {
      this.messages.add({
        severity: 'warn',
        summary: 'Copy unavailable',
        detail: 'Select the prompt text and copy it manually.',
      });
    }
  }
}
