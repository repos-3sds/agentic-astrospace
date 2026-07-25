create extension if not exists vector with schema extensions;

create table if not exists public.knowledge_sources (
  id uuid primary key default gen_random_uuid(),
  source_key text not null unique,
  title text not null,
  author text,
  edition text,
  language text,
  file_type text not null default 'epub',
  storage_bucket text not null,
  storage_path text not null,
  sha256 text not null,
  parser_version text not null,
  status text not null default 'processing'
    check (status in ('processing', 'ready', 'needs_review', 'failed')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.knowledge_sections (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.knowledge_sources(id) on delete cascade,
  ordinal integer not null,
  href text not null,
  title text,
  page_label text,
  exact_text text not null,
  text_sha256 text not null,
  raw_xhtml_sha256 text not null,
  extraction_confidence double precision,
  metadata jsonb not null default '{}'::jsonb,
  unique (source_id, ordinal)
);

create table if not exists public.knowledge_chunks (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.knowledge_sources(id) on delete cascade,
  ordinal integer not null,
  title text,
  content text not null,
  content_sha256 text not null,
  start_block_id text not null,
  end_block_id text not null,
  section_ordinals integer[] not null default '{}',
  page_labels text[] not null default '{}',
  domains text[] not null default '{}',
  subdomains text[] not null default '{}',
  topics text[] not null default '{}',
  content_types text[] not null default '{}',
  classification_confidence double precision,
  extraction_confidence double precision,
  quality_status text not null default 'needs_review'
    check (quality_status in ('published', 'needs_review', 'rejected')),
  quality_notes text[] not null default '{}',
  embedding extensions.vector(384),
  embedding_provider text,
  metadata jsonb not null default '{}'::jsonb,
  search_vector tsvector generated always as (
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', content), 'B')
  ) stored,
  unique (source_id, ordinal)
);

create index if not exists knowledge_chunks_domains_idx
  on public.knowledge_chunks using gin (domains);
create index if not exists knowledge_chunks_topics_idx
  on public.knowledge_chunks using gin (topics);
create index if not exists knowledge_chunks_search_idx
  on public.knowledge_chunks using gin (search_vector);
create index if not exists knowledge_chunks_embedding_idx
  on public.knowledge_chunks using hnsw (embedding extensions.vector_cosine_ops);

alter table public.knowledge_sources enable row level security;
alter table public.knowledge_sections enable row level security;
alter table public.knowledge_chunks enable row level security;

revoke all on public.knowledge_sources from anon, authenticated;
revoke all on public.knowledge_sections from anon, authenticated;
revoke all on public.knowledge_chunks from anon, authenticated;

create or replace function public.search_knowledge_chunks(
  query_text text,
  query_embedding extensions.vector(384) default null,
  filter_domains text[] default null,
  result_limit integer default 10
)
returns table (
  id uuid,
  source_id uuid,
  title text,
  content text,
  page_labels text[],
  domains text[],
  topics text[],
  quality_status text,
  lexical_score real,
  semantic_score real
)
language sql
stable
security invoker
set search_path = public, extensions
as $$
  select
    c.id,
    c.source_id,
    c.title,
    c.content,
    c.page_labels,
    c.domains,
    c.topics,
    c.quality_status,
    ts_rank_cd(c.search_vector, websearch_to_tsquery('english', query_text))::real,
    case
      when query_embedding is null or c.embedding is null then 0::real
      else (1 - (c.embedding <=> query_embedding))::real
    end
  from public.knowledge_chunks c
  where c.quality_status = 'published'
    and (
      filter_domains is null
      or cardinality(filter_domains) = 0
      or c.domains && filter_domains
    )
  order by (
    ts_rank_cd(c.search_vector, websearch_to_tsquery('english', query_text)) * 0.55
    + case
        when query_embedding is null or c.embedding is null then 0
        else (1 - (c.embedding <=> query_embedding)) * 0.45
      end
  ) desc
  limit least(greatest(result_limit, 1), 30);
$$;

revoke all on function public.search_knowledge_chunks(text, extensions.vector, text[], integer)
  from public, anon, authenticated;
grant execute on function public.search_knowledge_chunks(text, extensions.vector, text[], integer)
  to service_role;
