import { Injectable, inject } from '@angular/core';

import { ApiService } from './api.service';

export type ProfileFactKey =
  | 'employment_status'
  | 'relationship_status'
  | 'has_children'
  | 'occupation';

export interface ProfileContextFact {
  id: string;
  ref: string;
  category: string;
  key: ProfileFactKey;
  value: Record<string, unknown>;
  valid_from: string | null;
  valid_to: string | null;
  status: 'active' | 'disputed' | 'superseded' | 'deleted';
  sensitivity: string;
  source: { kind: string; channel: string };
  revision: number;
}

export interface ProfileContextProjection {
  profile_id: string;
  revision: number;
  as_of: string;
  status: 'ready' | 'context_confirmation_needed';
  contradictions: string[];
  facts: ProfileContextFact[];
  logical_constraints: string[];
}

export interface ProfileFactInput {
  key: ProfileFactKey;
  value: Record<string, unknown>;
  valid_from?: string | null;
  valid_to?: string | null;
}

@Injectable({ providedIn: 'root' })
export class ProfileContextService {
  private readonly api = inject(ApiService);

  load(profileId: string): Promise<ProfileContextProjection> {
    return this.api.get(`/profiles/${profileId}/context`);
  }

  create(profileId: string, revision: number, input: ProfileFactInput) {
    return this.api.post<{ revision: number; fact: ProfileContextFact }>(
      `/profiles/${profileId}/context/facts`, this.body(revision, input, 'profile_form'),
      { 'Idempotency-Key': this.idempotencyKey('create') },
    );
  }

  correct(profileId: string, factId: string, revision: number, input: ProfileFactInput) {
    return this.api.patch<{ revision: number; fact: ProfileContextFact }>(
      `/profiles/${profileId}/context/facts/${factId}`,
      this.body(revision, input, 'reader_correction'),
      { 'Idempotency-Key': this.idempotencyKey('correct') },
    );
  }

  remove(profileId: string, factId: string, revision: number) {
    return this.api.deleteWithBody<{ revision: number; fact_id: string; status: string }>(
      `/profiles/${profileId}/context/facts/${factId}`, { expected_revision: revision },
      { 'Idempotency-Key': this.idempotencyKey('delete') },
    );
  }

  export(profileId: string): Promise<{ schema_version: string; facts: ProfileContextFact[] }> {
    return this.api.get(`/profiles/${profileId}/context/export`);
  }

  private body(revision: number, input: ProfileFactInput, kind: 'profile_form' | 'reader_correction') {
    return {
      expected_revision: revision,
      key: input.key,
      value: input.value,
      valid_from: input.valid_from ?? null,
      valid_to: input.valid_to ?? null,
      source: { kind, channel: 'profile_settings' },
      consent: { state: 'granted', surface: 'profile_memory_v1' },
    };
  }

  private idempotencyKey(action: string): string {
    return `${action}-${crypto.randomUUID()}`;
  }
}
