-- Guard the hybrid search RPC against NaN semantic scores.
--
-- pgvector's cosine distance is undefined against a zero-magnitude embedding
-- and evaluates to NaN. The previous definition guarded `c.embedding is null`
-- but not a vector that is present and all zeros — which is what
-- FeatureHashEmbedder produces for text containing no Latin-alphabet tokens
-- (Devanagari verses, and table extractions with no words at all).
--
-- Postgres orders NaN as greater than every real value, so under
-- `order by ... desc` those chunks took the whole top of the ranking for every
-- query regardless of what was asked. Twelve chunks out of 1438 were enough to
-- displace the genuine matches from every result set.
--
-- Clamping the score in the application cannot fix this: ORDER BY and LIMIT
-- have already run in the database, so the real passages are discarded before
-- any client sees them. The guard has to live here.

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
      -- nullif catches NaN because Postgres defines NaN = NaN as true.
      else coalesce(
        nullif(1 - (c.embedding <=> query_embedding), 'NaN'::float8), 0
      )::real
    end
  from public.knowledge_chunks c
  where c.quality_status = 'published'
    and c.retrieval_scope = 'core'
    and (
      filter_domains is null
      or cardinality(filter_domains) = 0
      or c.domains && filter_domains
    )
  order by (
    ts_rank_cd(c.search_vector, websearch_to_tsquery('english', query_text)) * 0.55
    + case
        when query_embedding is null or c.embedding is null then 0
        else coalesce(
          nullif(1 - (c.embedding <=> query_embedding), 'NaN'::float8), 0
        ) * 0.45
      end
  ) desc
  limit least(greatest(result_limit, 1), 30);
$$;
