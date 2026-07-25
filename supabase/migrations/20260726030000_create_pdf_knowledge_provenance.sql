alter table public.knowledge_sections
  add column if not exists page_image_path text,
  add column if not exists page_image_sha256 text,
  add column if not exists extraction_method text;

alter table public.knowledge_chunks
  add column if not exists source_domains text[] not null default '{}';

create index if not exists knowledge_chunks_source_domains_idx
  on public.knowledge_chunks using gin (source_domains);

create or replace function public.prevent_knowledge_source_text_update()
returns trigger
language plpgsql
as $$
begin
  if tg_table_name = 'knowledge_sections'
     and (old.exact_text is distinct from new.exact_text
          or old.text_sha256 is distinct from new.text_sha256
          or old.raw_xhtml_sha256 is distinct from new.raw_xhtml_sha256
          or old.page_image_path is distinct from new.page_image_path
          or old.page_image_sha256 is distinct from new.page_image_sha256) then
    raise exception 'extracted source evidence and hashes are immutable; re-ingest the source';
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

drop function if exists public.search_knowledge_chunks(
  text, extensions.vector, text[], integer
);

create function public.search_knowledge_chunks(
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
  source_domains text[],
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
    c.source_domains,
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

revoke all on function public.search_knowledge_chunks(
  text, extensions.vector, text[], integer
) from public, anon, authenticated;

grant execute on function public.search_knowledge_chunks(
  text, extensions.vector, text[], integer
) to service_role;
