-- The agent-written "About you two" section of a full compatibility report
-- (astrospace/agents/compat_insight_agent.py), written once per pair and kept.
--
-- Only the API reads and writes it, as the backend role. RLS is on with no
-- policy and both client roles lose every grant, so no client can list
-- another reader's text (the 2026-10-18 audit's S2/S21 rule for new tables).
create table if not exists public.compatibility_insights (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  kundli_id text not null references public.kundlis(id) on delete cascade,
  partner_kundli_id text not null references public.kundlis(id) on delete cascade,
  key text not null,
  stage text not null default 'married' check (stage in ('married', 'planning')),
  payload jsonb not null,
  created_at timestamptz not null default now(),
  constraint compatibility_insights_pair_key unique (kundli_id, partner_kundli_id, key)
);

create index if not exists compatibility_insights_user_created
  on public.compatibility_insights(user_id, created_at desc);
create index if not exists compatibility_insights_partner
  on public.compatibility_insights(partner_kundli_id);

alter table public.compatibility_insights enable row level security;

do $$
declare
  r text;
begin
  foreach r in array array['authenticated', 'anon'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      execute format('revoke all on public.compatibility_insights from %I', r);
    end if;
  end loop;
end $$;
