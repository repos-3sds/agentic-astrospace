-- The agent-written Your Story for one profile
-- (astrospace/agents/story_agent.py), written once and kept until the birth
-- details, the prompt version or the running periods change.
--
-- Only the API reads and writes it, as the backend role. RLS is on with no
-- policy and both client roles lose every grant, so no client can list
-- another reader's text (the 2026-10-18 audit's S2/S21 rule for new tables).
create table if not exists public.life_stories (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  kundli_id text not null references public.kundlis(id) on delete cascade,
  key text not null,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  constraint life_stories_kundli_key unique (kundli_id, key)
);

create index if not exists life_stories_user_created
  on public.life_stories(user_id, created_at desc);

alter table public.life_stories enable row level security;

do $$
declare
  r text;
begin
  foreach r in array array['authenticated', 'anon'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      execute format('revoke all on public.life_stories from %I', r);
    end if;
  end loop;
end $$;
