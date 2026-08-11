import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';
import { MessageService } from 'primeng/api';
import { Toast } from 'primeng/toast';

import {
  AdminIdentity,
  AdminOverview,
  AdminService,
  AdminUserRow,
  AgentPromptRegistry,
  AuditEntry,
  KnowledgeChunk,
  KnowledgeSource,
  RetrievalScope,
  TaxonomyDomain,
} from '../../core/admin.service';
import { AuthService } from '../../core/auth.service';
import { ThemeService } from '../../core/theme.service';
import { AdminAgentPromptsComponent } from './admin-agent-prompts.component';

type ConsoleView =
  | 'overview'
  | 'users'
  | 'activity'
  | 'sources'
  | 'review'
  | 'retrieval'
  | 'prompts'
  | 'audit'
  | 'system';

const NAV: Array<{ id: ConsoleView; label: string; icon: string }> = [
  { id: 'overview', label: 'Overview', icon: 'layout-dashboard' },
  { id: 'users', label: 'Users', icon: 'users' },
  { id: 'activity', label: 'Product activity', icon: 'activity' },
  { id: 'sources', label: 'Knowledge sources', icon: 'library' },
  { id: 'review', label: 'Review queue', icon: 'clipboard-check' },
  { id: 'retrieval', label: 'Retrieval lab', icon: 'flask-conical' },
  { id: 'prompts', label: 'Agent prompts', icon: 'bot' },
  { id: 'audit', label: 'Audit log', icon: 'history' },
  { id: 'system', label: 'System health', icon: 'server-cog' },
];

@Component({
  selector: 'app-admin-console',
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    LucideAngularModule,
    Toast,
    AdminAgentPromptsComponent,
  ],
  templateUrl: './admin-console.component.html',
  styleUrl: './admin-console.component.scss',
})
export class AdminConsoleComponent implements OnInit {
  private admin = inject(AdminService);
  private auth = inject(AuthService);
  private messages = inject(MessageService);
  private router = inject(Router);
  protected theme = inject(ThemeService);

  protected readonly view = signal<ConsoleView>('overview');
  protected readonly identity = signal<AdminIdentity | null>(null);
  protected readonly nav = computed(() =>
    this.identity()?.role === 'admin'
      ? NAV
      : NAV.filter((item) => item.id !== 'prompts'),
  );
  protected readonly overview = signal<AdminOverview | null>(null);
  protected readonly sources = signal<KnowledgeSource[]>([]);
  protected readonly users = signal<AdminUserRow[]>([]);
  protected readonly selectedUser = signal<AdminUserRow | null>(null);
  protected readonly userDetail = signal<Record<string, any> | null>(null);
  protected readonly activity = signal<Record<string, any> | null>(null);
  protected readonly system = signal<Record<string, any> | null>(null);
  protected readonly chunks = signal<KnowledgeChunk[]>([]);
  protected readonly audit = signal<AuditEntry[]>([]);
  protected readonly taxonomy = signal<TaxonomyDomain[]>([]);
  protected readonly agentPrompts = signal<AgentPromptRegistry | null>(null);
  protected readonly selectedChunk = signal<KnowledgeChunk | null>(null);
  protected readonly selectedIds = signal<Set<string>>(new Set());
  protected readonly loading = signal(false);
  protected readonly error = signal('');
  protected readonly reviewReasonWarning = signal('');

  protected sourceStatus = 'all';
  protected sourceQuery = '';
  protected userQuery = '';
  protected userActionReason = '';
  protected chunkStatus = 'needs_review';
  protected chunkScope = 'all';
  protected chunkQuery = '';
  protected sourceFilter = '';
  protected reviewReason = '';
  protected editTitle = '';
  protected editTopics = '';
  protected editContentTypes = '';
  protected editSourceDomains = '';
  protected editDomains: string[] = [];
  protected editRetrievalScope: RetrievalScope = 'core';
  protected editRetrievalExclusionReason = '';
  protected selectedPageIndex = 0;
  protected retrievalQuery = '';
  protected retrievalDomains: string[] = [];
  protected retrievalResults = signal<Array<Record<string, any>>>([]);
  protected retrievalLoading = signal(false);
  protected readonly uploadOpen = signal(false);
  protected uploadFile: File | null = null;
  protected uploadSourceKey = '';
  protected uploadStartSection = 0;
  protected uploadMaxSections: number | null = null;

  protected readonly queueCount = computed(
    () => this.overview()?.chunks?.['needs_review'] ?? this.chunks().length,
  );
  protected readonly allSelected = computed(
    () => this.chunks().length > 0 && this.selectedIds().size === this.chunks().length,
  );

  async ngOnInit(): Promise<void> {
    await this.loadInitial();
  }

  protected async switchView(view: ConsoleView): Promise<void> {
    this.view.set(view);
    this.selectedChunk.set(null);
    if (view === 'overview') await this.loadOverview();
    if (view === 'users') await this.loadUsers();
    if (view === 'activity') await this.loadActivity();
    if (view === 'sources') await this.loadSources();
    if (view === 'review') await this.loadChunks();
    if (view === 'prompts') await this.loadAgentPrompts();
    if (view === 'audit') await this.loadAudit();
    if (view === 'system') await this.loadSystem();
  }

  private async loadInitial(): Promise<void> {
    this.loading.set(true);
    try {
      const [identity, overview, taxonomy] = await Promise.all([
        this.admin.me(),
        this.admin.overview(),
        this.admin.taxonomy(),
      ]);
      this.identity.set(identity);
      this.overview.set(overview);
      this.taxonomy.set(taxonomy.domains);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  protected async loadOverview(): Promise<void> {
    await this.run(async () => this.overview.set(await this.admin.overview()));
  }

  protected async loadSources(): Promise<void> {
    await this.run(async () =>
      this.sources.set(await this.admin.sources(this.sourceStatus, this.sourceQuery.trim())),
    );
  }

  protected async loadUsers(): Promise<void> {
    await this.run(async () =>
      this.users.set(await this.admin.users(this.userQuery.trim())),
    );
  }

  protected async loadActivity(): Promise<void> {
    await this.run(async () => this.activity.set(await this.admin.activity()));
  }

  protected async loadSystem(): Promise<void> {
    await this.run(async () => this.system.set(await this.admin.system()));
  }

  protected async loadChunks(): Promise<void> {
    await this.run(async () => {
      this.chunks.set(
        await this.admin.chunks(
          this.chunkStatus,
          this.sourceFilter || undefined,
          this.chunkQuery.trim(),
          this.chunkScope,
        ),
      );
      this.selectedIds.set(new Set());
    });
  }

  protected async loadAudit(): Promise<void> {
    await this.run(async () => this.audit.set(await this.admin.audit()));
  }

  protected async loadAgentPrompts(): Promise<void> {
    await this.run(async () => this.agentPrompts.set(await this.admin.agentPrompts()));
  }

  protected openSource(source: KnowledgeSource): void {
    this.sourceFilter = source.id;
    this.chunkStatus = 'all';
    void this.switchView('review');
  }

  protected async inspectUser(user: AdminUserRow): Promise<void> {
    this.selectedUser.set(user);
    this.userActionReason = '';
    await this.run(async () => this.userDetail.set(await this.admin.userDetail(user.id)));
  }

  protected closeUserInspector(): void {
    this.selectedUser.set(null);
    this.userDetail.set(null);
  }

  protected async setUserStatus(action: 'suspend' | 'restore'): Promise<void> {
    const user = this.selectedUser();
    if (!user || !this.requireUserReason()) return;
    await this.runAction(async () => {
      await this.admin.updateUserStatus(user.id, action, this.userActionReason.trim());
      this.toast(
        action === 'suspend' ? 'User suspended' : 'User restored',
        'The account action was recorded in the audit log.',
      );
      this.closeUserInspector();
      await this.loadUsers();
    });
  }

  protected async setAdminAccess(
    role: 'admin' | 'reviewer',
    active: boolean,
  ): Promise<void> {
    const user = this.selectedUser();
    if (!user || !this.requireUserReason()) return;
    await this.runAction(async () => {
      await this.admin.updateAccess(user.id, role, active, this.userActionReason.trim());
      this.toast(
        active ? `${role} access granted` : 'Console access removed',
        'The permission change was recorded.',
      );
      await this.loadUsers();
      const refreshed = this.users().find((row) => row.id === user.id);
      if (refreshed) this.selectedUser.set(refreshed);
    });
  }

  protected onUploadFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.uploadFile = input.files?.[0] ?? null;
    if (this.uploadFile && !this.uploadSourceKey) {
      this.uploadSourceKey = this.uploadFile.name
        .replace(/\.(epub|pdf)$/i, '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '');
    }
  }

  protected async uploadSource(): Promise<void> {
    if (!this.uploadFile || !this.uploadSourceKey) {
      this.toast('Source and key required', 'Choose a PDF or EPUB and provide its stable key.', 'warn');
      return;
    }
    await this.runAction(async () => {
      const form = new FormData();
      form.append('file', this.uploadFile!);
      form.append('source_key', this.uploadSourceKey);
      form.append('start_section', String(this.uploadStartSection || 0));
      if (this.uploadMaxSections) form.append('max_sections', String(this.uploadMaxSections));
      const result = await this.admin.uploadSource(form);
      this.uploadOpen.set(false);
      this.toast('Ingestion queued', `Run ${result.run_id.slice(0, 8)} is now processing.`);
      await this.loadSystem();
    });
  }

  protected async inspectChunk(chunk: KnowledgeChunk): Promise<void> {
    this.populateChunkEditor(chunk);
    try {
      const detail = await this.admin.chunkDetail(chunk.id);
      this.populateChunkEditor({
        ...chunk,
        ...detail.chunk,
        source: detail.source || chunk.source,
      });
    } catch (error) {
      this.toast('Page proof unavailable', (error as Error).message, 'warn');
    }
  }

  private populateChunkEditor(chunk: KnowledgeChunk): void {
    this.selectedChunk.set(chunk);
    this.editTitle = chunk.title || '';
    this.editTopics = (chunk.topics || []).join(', ');
    this.editContentTypes = (chunk.content_types || []).join(', ');
    this.editSourceDomains = (chunk.source_domains || []).join(', ');
    this.editDomains = [...(chunk.domains || [])];
    this.editRetrievalScope = chunk.retrieval_scope || 'core';
    this.editRetrievalExclusionReason = chunk.retrieval_exclusion_reason || '';
    this.reviewReason = '';
    this.selectedPageIndex = 0;
  }

  protected closeInspector(): void {
    this.selectedChunk.set(null);
  }

  protected domainSelected(id: string): boolean {
    return this.editDomains.includes(id);
  }

  protected toggleDomain(id: string): void {
    this.editDomains = this.domainSelected(id)
      ? this.editDomains.filter((value) => value !== id)
      : [...this.editDomains, id];
  }

  protected toggleSelection(id: string): void {
    const next = new Set(this.selectedIds());
    next.has(id) ? next.delete(id) : next.add(id);
    this.selectedIds.set(next);
  }

  protected toggleAll(): void {
    this.selectedIds.set(
      this.allSelected() ? new Set() : new Set(this.chunks().map((chunk) => chunk.id)),
    );
  }

  protected async saveMetadata(): Promise<void> {
    const chunk = this.selectedChunk();
    if (!chunk || !this.requireReason()) return;
    await this.runAction(async () => {
      const updated = await this.admin.updateChunkMetadata(chunk.id, {
        title: this.editTitle.trim(),
        domains: this.editDomains,
        topics: this.csv(this.editTopics),
        content_types: this.csv(this.editContentTypes),
        source_domains: this.csv(this.editSourceDomains),
        retrieval_scope: this.editRetrievalScope,
        retrieval_exclusion_reason: (
          this.editRetrievalScope === 'core'
            ? ''
            : this.editRetrievalExclusionReason.trim()
        ),
        reason: this.reviewReason.trim(),
      });
      this.replaceChunk(updated);
      await this.inspectChunk({ ...chunk, ...updated, source: chunk.source });
      this.toast('Metadata saved', 'The source passage itself was not changed.');
    });
  }

  protected async review(action: 'publish' | 'reject' | 'requeue'): Promise<void> {
    const chunk = this.selectedChunk();
    if (!chunk || !this.requireReason()) return;
    await this.runAction(async () => {
      await this.admin.reviewChunk(chunk.id, action, this.reviewReason.trim());
      this.chunks.update((rows) => rows.filter((row) => row.id !== chunk.id));
      this.selectedChunk.set(null);
      this.toast(
        action === 'publish' ? 'Passage published' : action === 'reject' ? 'Passage rejected' : 'Passage requeued',
        'The action was recorded in the audit log.',
      );
      await this.loadOverview();
    });
  }

  protected async bulkReview(action: 'publish' | 'reject' | 'requeue'): Promise<void> {
    if (!this.selectedIds().size || !this.requireReason()) return;
    await this.runAction(async () => {
      const ids = [...this.selectedIds()];
      await this.admin.bulkReview(ids, action, this.reviewReason.trim());
      this.chunks.update((rows) => rows.filter((row) => !this.selectedIds().has(row.id)));
      this.selectedIds.set(new Set());
      this.toast(`${ids.length} passages updated`, 'One request ID links the complete bulk action.');
      await this.loadOverview();
    });
  }

  protected async testRetrieval(): Promise<void> {
    if (this.retrievalQuery.trim().length < 2) return;
    this.retrievalLoading.set(true);
    try {
      const response = await this.admin.retrievalTest(
        this.retrievalQuery.trim(),
        this.retrievalDomains,
      );
      this.retrievalResults.set(response.results);
    } catch (error) {
      this.toast('Retrieval failed', (error as Error).message, 'error');
    } finally {
      this.retrievalLoading.set(false);
    }
  }

  protected toggleRetrievalDomain(id: string): void {
    this.retrievalDomains = this.retrievalDomains.includes(id)
      ? this.retrievalDomains.filter((value) => value !== id)
      : [...this.retrievalDomains, id];
  }

  protected async signOut(): Promise<void> {
    await this.auth.signOut();
    await this.router.navigate(['/']);
  }

  protected confidence(value?: number): string {
    return value == null ? 'Not reported' : `${Math.round(value * 100)}%`;
  }

  protected statusLabel(value: unknown): string {
    return String(value).replaceAll('_', ' ');
  }

  protected auditDetail(entry: AuditEntry): string {
    const actor = entry.actor_email || 'System';
    return `${actor} · ${entry.reason || 'No reason recorded'}`;
  }

  private csv(value: string): string[] {
    return [...new Set(value.split(',').map((item) => item.trim()).filter(Boolean))];
  }

  private requireReason(): boolean {
    if (this.reviewReason.trim().length >= 3) {
      this.reviewReasonWarning.set('');
      return true;
    }
    this.reviewReasonWarning.set('Add a short audit reason before publishing or rejecting.');
    setTimeout(() => document.getElementById('admin-review-reason')?.focus(), 0);
    this.toast('Reason required', 'Add a short reason so the audit record is meaningful.', 'warn');
    return false;
  }

  private requireUserReason(): boolean {
    if (this.userActionReason.trim().length >= 3) return true;
    this.toast('Reason required', 'Add a reason for this account or permission change.', 'warn');
    return false;
  }

  private replaceChunk(updated: KnowledgeChunk): void {
    this.chunks.update((rows) =>
      rows.map((row) => (row.id === updated.id ? { ...row, ...updated, source: row.source } : row)),
    );
  }

  private async run(action: () => Promise<void>): Promise<void> {
    this.loading.set(true);
    this.error.set('');
    try {
      await action();
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  private async runAction(action: () => Promise<void>): Promise<void> {
    this.loading.set(true);
    try {
      await action();
    } catch (error) {
      this.toast('Action failed', (error as Error).message, 'error');
    } finally {
      this.loading.set(false);
    }
  }

  private toast(summary: string, detail: string, severity = 'success'): void {
    this.messages.add({ severity, summary, detail });
  }
}
