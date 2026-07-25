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
      or cardinality(c.domains) = 0
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
