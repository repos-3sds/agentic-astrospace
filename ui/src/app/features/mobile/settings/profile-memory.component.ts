import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import {
  ProfileContextFact,
  ProfileContextService,
  ProfileFactInput,
  ProfileFactKey,
} from '../../../core/profile-context.service';

type EditorKind = ProfileFactKey;

@Component({
  selector: 'as-profile-memory',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './profile-memory.component.html',
  styleUrl: './profile-memory.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProfileMemoryComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly context = inject(ProfileContextService);
  protected readonly kundlis = inject(KundliStore);

  protected readonly profileId = signal('');
  protected readonly loading = signal(true);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly revision = signal(0);
  protected readonly facts = signal<ProfileContextFact[]>([]);
  protected readonly contradictions = signal<string[]>([]);
  protected readonly editorOpen = signal(false);
  protected readonly editing = signal<ProfileContextFact | null>(null);
  protected readonly pendingDelete = signal<string | null>(null);

  protected editorKind: EditorKind = 'employment_status';
  protected editorValue = '';
  protected validFrom = '';

  protected readonly profile = computed(
    () => this.kundlis.kundlis().find((item) => item.id === this.profileId()) ?? null,
  );

  constructor() {
    void this.kundlis.load();
    this.route.paramMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      this.profileId.set(params.get('id') ?? '');
      this.busy.set(false);
      this.pendingDelete.set(null);
      this.closeEditor();
      void this.load();
    });
  }

  protected openAdd(): void {
    this.editing.set(null);
    this.editorKind = 'employment_status';
    this.editorValue = 'employed';
    this.validFrom = '';
    this.editorOpen.set(true);
  }

  protected openEdit(fact: ProfileContextFact): void {
    this.editing.set(fact);
    this.editorKind = fact.key;
    this.editorValue = this.rawValue(fact);
    this.validFrom = fact.valid_from ?? '';
    this.editorOpen.set(true);
  }

  protected closeEditor(): void {
    this.editorOpen.set(false);
    this.editing.set(null);
    this.error.set(null);
  }

  protected editorChanged(): void {
    this.editorValue = this.editorKind === 'occupation'
      ? ''
      : (this.options(this.editorKind)[0]?.value ?? '');
  }

  protected async save(): Promise<void> {
    if (!this.editorValue.trim() || this.busy()) return;
    const requestedProfile = this.profileId();
    this.busy.set(true);
    this.error.set(null);
    try {
      const editing = this.editing();
      if (editing) {
        await this.context.correct(requestedProfile, editing.id, this.revision(), this.input());
      } else {
        await this.context.create(requestedProfile, this.revision(), this.input());
      }
      if (requestedProfile !== this.profileId()) return;
      this.closeEditor();
      await this.load();
    } catch (error) {
      if (requestedProfile === this.profileId()) {
        await this.refreshAfterConflict(error);
        this.error.set(this.message(error));
      }
    } finally {
      if (requestedProfile === this.profileId()) this.busy.set(false);
    }
  }

  protected askDelete(factId: string): void {
    this.pendingDelete.set(factId);
  }

  protected async remove(factId: string): Promise<void> {
    const requestedProfile = this.profileId();
    this.busy.set(true);
    this.error.set(null);
    try {
      await this.context.remove(requestedProfile, factId, this.revision());
      if (requestedProfile !== this.profileId()) return;
      this.pendingDelete.set(null);
      await this.load();
    } catch (error) {
      if (requestedProfile === this.profileId()) {
        await this.refreshAfterConflict(error);
        this.error.set(this.message(error));
      }
    } finally {
      if (requestedProfile === this.profileId()) this.busy.set(false);
    }
  }

  protected async exportMemory(): Promise<void> {
    const requestedProfile = this.profileId();
    this.busy.set(true);
    this.error.set(null);
    try {
      const payload = await this.context.export(requestedProfile);
      if (requestedProfile !== this.profileId()) return;
      const file = new File(
        [JSON.stringify(payload, null, 2)],
        `siddha-profile-memory-${requestedProfile}.json`,
        { type: 'application/json' },
      );
      if (navigator.share && navigator.canShare?.({ files: [file] })) {
        await navigator.share({ title: 'Siddha profile memory', files: [file] });
      } else {
        const url = URL.createObjectURL(file);
        const link = document.createElement('a');
        link.href = url;
        link.download = file.name;
        link.click();
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      if (
        requestedProfile === this.profileId()
        && (error as DOMException).name !== 'AbortError'
      ) {
        this.error.set(this.message(error));
      }
    } finally {
      if (requestedProfile === this.profileId()) this.busy.set(false);
    }
  }

  protected label(fact: ProfileContextFact): string {
    return ({
      employment_status: 'Work status', relationship_status: 'Relationship',
      has_children: 'Children', occupation: 'Occupation',
    } as Record<string, string>)[fact.key] ?? fact.key;
  }

  protected displayValue(fact: ProfileContextFact): string {
    const raw = this.rawValue(fact);
    if (fact.key === 'has_children') return raw === 'true' ? 'Has children' : 'No children recorded';
    return raw.replaceAll('_', ' ').replace(/^./, (value) => value.toUpperCase());
  }

  protected options(kind: EditorKind): { value: string; label: string }[] {
    const values: Record<Exclude<EditorKind, 'occupation'>, string[][]> = {
      employment_status: [
        ['employed', 'Employed'], ['self_employed', 'Self-employed'],
        ['unemployed', 'Not currently working'], ['student', 'Student'], ['retired', 'Retired'],
      ],
      relationship_status: [
        ['single', 'Single'], ['partnered', 'Partnered'], ['engaged', 'Engaged'],
        ['married', 'Married'], ['separated', 'Separated'], ['divorced', 'Divorced'],
        ['widowed', 'Widowed'],
      ],
      has_children: [['true', 'Has children'], ['false', 'Does not have children']],
    };
    if (kind === 'occupation') return [];
    return values[kind].map(([value, label]) => ({ value, label }));
  }

  private async load(): Promise<void> {
    const requestedProfile = this.profileId();
    if (!requestedProfile) return;
    this.loading.set(true);
    this.error.set(null);
    try {
      const projection = await this.context.load(requestedProfile);
      if (requestedProfile !== this.profileId()) return;
      this.revision.set(projection.revision);
      this.facts.set(projection.facts.filter((fact) => fact.status === 'active'));
      this.contradictions.set(projection.contradictions);
    } catch (error) {
      if (requestedProfile === this.profileId()) this.error.set(this.message(error));
    } finally {
      if (requestedProfile === this.profileId()) this.loading.set(false);
    }
  }

  private input(): ProfileFactInput {
    const key = this.editorKind;
    const value = key === 'has_children'
      ? { value: this.editorValue === 'true' }
      : key === 'occupation'
        ? { text: this.editorValue.trim() }
        : { code: this.editorValue };
    return { key, value, valid_from: this.validFrom || null };
  }

  private rawValue(fact: ProfileContextFact): string {
    if ('code' in fact.value) return String(fact.value['code']);
    if ('text' in fact.value) return String(fact.value['text']);
    return String(fact.value['value']);
  }

  private message(error: unknown): string {
    const message = (error as Error).message || 'Profile memory could not be updated.';
    return message.includes('stale_revision')
      ? 'This profile changed on another screen or device. Latest memory has been loaded.'
      : message;
  }

  private async refreshAfterConflict(error: unknown): Promise<void> {
    if ((error as Error).message?.includes('stale_revision')) await this.load();
  }
}
