drop trigger if exists knowledge_sections_text_immutable
  on public.knowledge_sections;
drop trigger if exists knowledge_chunks_text_immutable
  on public.knowledge_chunks;

create or replace function public.prevent_knowledge_section_text_update()
returns trigger
language plpgsql
as $$
begin
  if old.exact_text is distinct from new.exact_text
     or old.text_sha256 is distinct from new.text_sha256
     or old.raw_xhtml_sha256 is distinct from new.raw_xhtml_sha256
     or old.page_image_path is distinct from new.page_image_path
     or old.page_image_sha256 is distinct from new.page_image_sha256 then
    raise exception 'extracted source evidence and hashes are immutable; re-ingest the source';
  end if;
  return new;
end;
$$;

create or replace function public.prevent_knowledge_chunk_text_update()
returns trigger
language plpgsql
as $$
begin
  if old.content is distinct from new.content
     or old.content_sha256 is distinct from new.content_sha256
     or old.start_block_id is distinct from new.start_block_id
     or old.end_block_id is distinct from new.end_block_id then
    raise exception 'chunk source text and boundaries are immutable; re-ingest the source';
  end if;
  return new;
end;
$$;

create trigger knowledge_sections_text_immutable
before update on public.knowledge_sections
for each row execute function public.prevent_knowledge_section_text_update();

create trigger knowledge_chunks_text_immutable
before update on public.knowledge_chunks
for each row execute function public.prevent_knowledge_chunk_text_update();

drop function if exists public.prevent_knowledge_source_text_update();
