import { importProvidersFrom } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import {
  Boxes,
  ChevronRight,
  ClipboardCheck,
  LucideAngularModule,
  NotebookPen,
  ShieldCheck,
  Sparkles,
} from 'lucide-angular';
import { MessageService } from 'primeng/api';

import { AgentPromptRegistry } from '../../core/admin.service';
import { AdminAgentPromptsComponent } from './admin-agent-prompts.component';

const REGISTRY: AgentPromptRegistry = {
  schema_version: 'agent_prompt_registry_v1',
  base: {
    name: 'Base grounding prompt',
    source_file: 'astrospace/agents/domain_agent.py',
    symbol: '_BASE_SYSTEM',
    prompt: 'Ground every claim in the supplied bundle.',
  },
  composition: {
    owner: 'DomainReadingAgent.__init__',
    description: 'Composes the live specialist prompt.',
    runtime_inputs: ['bundle_json', 'domain_addendum'],
  },
  coverage: {
    configured: 1,
    taxonomy_total: 2,
    unconfigured: [{ id: 'health', name: 'Health' }],
  },
  domains: [{
    id: 'career',
    name: 'Career & Profession',
    description: 'Career guidance.',
    source_file: 'astrospace/agents/registry.py',
    symbol: '_CAREER_ADDENDUM',
    addendum: 'Use D10 as primary career evidence.',
  }],
  editable: false,
};

describe('AdminAgentPromptsComponent', () => {
  it('renders the live base prompt and switches to a domain addendum', async () => {
    await TestBed.configureTestingModule({
      imports: [AdminAgentPromptsComponent],
      providers: [
        MessageService,
        importProvidersFrom(LucideAngularModule.pick({
          Boxes,
          ChevronRight,
          ClipboardCheck,
          NotebookPen,
          ShieldCheck,
          Sparkles,
        })),
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(AdminAgentPromptsComponent);
    fixture.componentRef.setInput('registry', REGISTRY);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Ground every claim in the supplied bundle.');
    expect(fixture.nativeElement.textContent).toContain('Health');
    expect(fixture.nativeElement.textContent).toContain('domain_not_ready');

    const buttons = [...fixture.nativeElement.querySelectorAll('.prompt-index button')] as HTMLButtonElement[];
    buttons.find((button) => button.textContent?.includes('Career & Profession'))?.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Use D10 as primary career evidence.');
    expect(fixture.nativeElement.textContent).toContain('_CAREER_ADDENDUM');
  });
});
