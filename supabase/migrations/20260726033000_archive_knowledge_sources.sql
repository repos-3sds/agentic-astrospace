alter table public.knowledge_sources
  drop constraint if exists knowledge_sources_status_check;

alter table public.knowledge_sources
  add constraint knowledge_sources_status_check
  check (status in (
    'processing',
    'ready',
    'needs_review',
    'failed',
    'archived'
  ));
