create table if not exists public.admin_users (
  user_id uuid primary key references auth.users(id) on delete cascade,
  role text not null default 'reviewer'
    check (role in ('admin', 'reviewer')),
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.knowledge_ingestion_runs (
  id uuid primary key default gen_random_uuid(),
  source_id uuid references public.knowledge_sources(id) on delete set null,
  source_key text not null,
  status text not null default 'queued'
    check (status in ('queued', 'running', 'completed', 'failed')),
  requested_by uuid references auth.users(id) on delete set null,
  analyzer_model text,
  start_section integer not null default 0,
  max_sections integer,
  sections_count integer,
  chunks_count integer,
  published_count integer,
  review_count integer,
  error_message text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.knowledge_audit_log (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid references auth.users(id) on delete set null,
  actor_email text,
  actor_role text,
  action text not null,
  entity_type text not null,
  entity_id text,
  source_id uuid references public.knowledge_sources(id) on delete set null,
  reason text,
  before_state jsonb,
  after_state jsonb,
  request_id uuid not null default gen_random_uuid(),
  created_at timestamptz not null default now()
);

create index if not exists knowledge_audit_created_idx
  on public.knowledge_audit_log (created_at desc);
create index if not exists knowledge_audit_source_idx
  on public.knowledge_audit_log (source_id, created_at desc);
create index if not exists knowledge_ingestion_runs_created_idx
  on public.knowledge_ingestion_runs (created_at desc);

alter table public.admin_users enable row level security;
alter table public.knowledge_ingestion_runs enable row level security;
alter table public.knowledge_audit_log enable row level security;

revoke all on public.admin_users from anon, authenticated;
revoke all on public.knowledge_ingestion_runs from anon, authenticated;
revoke all on public.knowledge_audit_log from anon, authenticated;

create or replace function public.prevent_knowledge_audit_mutation()
returns trigger
language plpgsql
as $$
begin
  raise exception 'knowledge_audit_log is append-only';
end;
$$;

drop trigger if exists knowledge_audit_immutable
  on public.knowledge_audit_log;
create trigger knowledge_audit_immutable
before update or delete on public.knowledge_audit_log
for each row execute function public.prevent_knowledge_audit_mutation();

create or replace function public.prevent_knowledge_source_text_update()
returns trigger
language plpgsql
as $$
begin
  if tg_table_name = 'knowledge_sections'
     and (old.exact_text is distinct from new.exact_text
          or old.text_sha256 is distinct from new.text_sha256
          or old.raw_xhtml_sha256 is distinct from new.raw_xhtml_sha256) then
    raise exception 'extracted source text and hashes are immutable; re-ingest the source';
  end if;
  if tg_table_name = 'knowledge_chunks'
     and (old.content is distinct from new.content
          or old.content_sha256 is distinct from new.content_sha256
          or old.start_block_id is distinct from new.start_block_id
          or old.end_block_id is distinct from new.end_block_id) then
    raise exception 'chunk source text and boundaries are immutable; re-ingest the source';
  end if;
  return new;
end;
$$;

drop trigger if exists knowledge_sections_text_immutable
  on public.knowledge_sections;
create trigger knowledge_sections_text_immutable
before update on public.knowledge_sections
for each row execute function public.prevent_knowledge_source_text_update();

drop trigger if exists knowledge_chunks_text_immutable
  on public.knowledge_chunks;
create trigger knowledge_chunks_text_immutable
before update on public.knowledge_chunks
for each row execute function public.prevent_knowledge_source_text_update();
