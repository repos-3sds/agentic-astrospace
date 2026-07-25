import { Injectable, inject } from '@angular/core';

import { ApiService } from './api.service';

export type ReviewStatus = 'published' | 'needs_review' | 'rejected';
export type RetrievalScope =
  | 'core'
  | 'editorial'
  | 'navigation'
  | 'publishing'
  | 'devotional'
  | 'out_of_domain';

export interface AdminIdentity {
  id: string;
  email: string;
  role: 'admin' | 'reviewer';
}

export interface KnowledgeSource {
  id: string;
  source_key: string;
  title: string;
  author?: string;
  edition?: string;
  language?: string;
  file_type: string;
  storage_bucket: string;
  storage_path: string;
  sha256: string;
  parser_version: string;
  status: string;
  updated_at: string;
  chunk_counts?: Record<string, number>;
}

export interface KnowledgeChunk {
  id: string;
  source_id: string;
  ordinal: number;
  title: string;
  content: string;
  page_labels: string[];
  section_ordinals: number[];
  domains: string[];
  subdomains: string[];
  source_domains: string[];
  topics: string[];
  content_types: string[];
  classification_confidence?: number;
  extraction_confidence?: number;
  quality_status: ReviewStatus;
  quality_notes: string[];
  content_sha256: string;
  retrieval_scope: RetrievalScope;
  retrieval_exclusion_reason?: string;
  scope_confidence?: number;
  scope_classifier?: string;
  page_assets?: Array<{
    id: string;
    ordinal: number;
    page_label?: string;
    title?: string;
    page_image_url?: string;
    page_image_sha256?: string;
    extraction_method?: string;
  }>;
  source?: KnowledgeSource;
}

export interface AuditEntry {
  id: string;
  actor_email?: string;
  actor_role?: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  source_id?: string;
  reason?: string;
  before_state?: unknown;
  after_state?: unknown;
  request_id: string;
  created_at: string;
}

export interface AdminOverview {
  role: string;
  users: Record<string, number>;
  product: Record<string, number>;
  sources: Record<string, number>;
  chunks: Record<string, number>;
  recent_sources: KnowledgeSource[];
  recent_runs: Record<string, unknown>[];
  recent_audit: AuditEntry[];
}

export interface AdminUserRow {
  id: string;
  email?: string;
  display_name?: string;
  avatar_url?: string;
  locale?: string;
  timezone?: string;
  providers: string[];
  created_at: string;
  last_sign_in_at?: string;
  banned_until?: string;
  profile_count: number;
  thread_count: number;
  device_count: number;
  admin_role?: 'admin' | 'reviewer';
  admin_active: boolean;
}

export interface TaxonomyDomain {
  id: string;
  name: string;
  description: string;
  subdomains: string[];
  keywords: string[];
}

@Injectable({ providedIn: 'root' })
export class AdminService {
  private api = inject(ApiService);

  me(): Promise<AdminIdentity> {
    return this.api.get('/admin/me');
  }

  overview(): Promise<AdminOverview> {
    return this.api.get('/admin/overview');
  }

  users(query?: string): Promise<AdminUserRow[]> {
    return this.api.get(`/admin/users${query ? `?q=${encodeURIComponent(query)}` : ''}`);
  }

  userDetail(id: string): Promise<Record<string, any>> {
    return this.api.get(`/admin/users/${id}`);
  }

  updateUserStatus(
    id: string,
    action: 'suspend' | 'restore',
    reason: string,
  ): Promise<Record<string, any>> {
    return this.api.post(`/admin/users/${id}/status`, { action, reason });
  }

  updateAccess(
    id: string,
    role: 'admin' | 'reviewer',
    active: boolean,
    reason: string,
  ): Promise<Record<string, any>> {
    return this.api.put(`/admin/access/${id}`, { role, active, reason });
  }

  activity(): Promise<Record<string, any>> {
    return this.api.get('/admin/activity');
  }

  system(): Promise<Record<string, any>> {
    return this.api.get('/admin/system');
  }

  sources(status?: string, query?: string): Promise<KnowledgeSource[]> {
    const params = new URLSearchParams();
    if (status && status !== 'all') params.set('status', status);
    if (query) params.set('q', query);
    const suffix = params.size ? `?${params}` : '';
    return this.api.get(`/admin/sources${suffix}`);
  }

  chunks(
    status = 'needs_review',
    sourceId?: string,
    query?: string,
    retrievalScope?: string,
  ): Promise<KnowledgeChunk[]> {
    const params = new URLSearchParams({ status });
    if (sourceId) params.set('source_id', sourceId);
    if (query) params.set('q', query);
    if (retrievalScope && retrievalScope !== 'all') {
      params.set('retrieval_scope', retrievalScope);
    }
    return this.api.get(`/admin/chunks?${params}`);
  }

  chunkDetail(id: string): Promise<{
    chunk: KnowledgeChunk;
    source: KnowledgeSource;
    audit: AuditEntry[];
  }> {
    return this.api.get(`/admin/chunks/${id}`);
  }

  taxonomy(): Promise<{ version: number; domains: TaxonomyDomain[] }> {
    return this.api.get('/admin/taxonomy');
  }

  updateChunkMetadata(
    id: string,
    payload: {
      title?: string;
      domains?: string[];
      subdomains?: string[];
      topics?: string[];
      content_types?: string[];
      source_domains?: string[];
      retrieval_scope?: RetrievalScope;
      retrieval_exclusion_reason?: string;
      reason: string;
    },
  ): Promise<KnowledgeChunk> {
    return this.api.patch(`/admin/chunks/${id}/metadata`, payload);
  }

  reviewChunk(
    id: string,
    action: 'publish' | 'reject' | 'requeue',
    reason: string,
  ): Promise<KnowledgeChunk> {
    return this.api.post(`/admin/chunks/${id}/review`, { action, reason });
  }

  bulkReview(
    chunkIds: string[],
    action: 'publish' | 'reject' | 'requeue',
    reason: string,
  ): Promise<{ updated: number; request_id: string }> {
    return this.api.post('/admin/chunks/bulk-review', {
      chunk_ids: chunkIds,
      action,
      reason,
    });
  }

  audit(sourceId?: string): Promise<AuditEntry[]> {
    return this.api.get(`/admin/audit${sourceId ? `?source_id=${sourceId}` : ''}`);
  }

  uploadSource(formData: FormData): Promise<{ run_id: string; status: string }> {
    return this.api.post('/admin/sources/upload', formData);
  }

  reprocessSource(
    sourceId: string,
    startSection = 0,
    maxSections?: number,
  ): Promise<{ run_id: string; status: string }> {
    const params = new URLSearchParams({ start_section: String(startSection) });
    if (maxSections) params.set('max_sections', String(maxSections));
    return this.api.post(`/admin/sources/${sourceId}/reprocess?${params}`, {});
  }

  retrievalTest(query: string, domains: string[], limit = 8): Promise<{
    query: string;
    domains: string[];
    results: Array<Record<string, any>>;
  }> {
    return this.api.post('/admin/retrieval/test', { query, domains, limit });
  }
}
