-- Explicit, profile-owned life context used to constrain interpretation.
-- Values are never inferred directly into this store and never alter chart math.

create table if not exists public.profile_context_ledgers (
  profile_id text primary key references public.kundlis(id) on delete cascade,
  user_id text not null,
  revision integer not null default 0 check (revision >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_profile_context_ledgers_user
  on public.profile_context_ledgers(user_id, profile_id);

create table if not exists public.profile_context_facts (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  profile_id text not null references public.kundlis(id) on delete cascade,
  category text not null,
  key text not null,
  value jsonb,
  valid_from date,
  valid_to date,
  status text not null default 'active'
    check (status in ('active', 'superseded', 'disputed', 'deleted')),
  confidence text not null default 'confirmed'
    check (confidence in ('confirmed', 'reported', 'candidate', 'disputed')),
  sensitivity text not null,
  retention text not null,
  source jsonb not null default '{}'::jsonb,
  consent jsonb not null default '{}'::jsonb,
  supersedes_id uuid references public.profile_context_facts(id) on delete set null,
  revision integer not null check (revision > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz,
  constraint profile_context_fact_dates_check
    check (valid_to is null or valid_from is null or valid_to >= valid_from),
  constraint profile_context_deleted_value_check
    check (status <> 'deleted' or (value is null and source = '{}'::jsonb and consent = '{}'::jsonb))
);

create index if not exists idx_profile_context_facts_projection
  on public.profile_context_facts(user_id, profile_id, status, key, revision);

create table if not exists public.profile_context_mutations (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  profile_id text not null references public.kundlis(id) on delete cascade,
  idempotency_key text not null,
  request_hash text not null,
  action text not null,
  fact_id uuid,
  resulting_revision integer not null,
  response jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(user_id, profile_id, idempotency_key)
);

create table if not exists public.profile_context_audit_events (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  profile_id text not null references public.kundlis(id) on delete cascade,
  fact_id uuid,
  action text not null,
  category text,
  key text,
  revision integer not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_profile_context_audit_profile
  on public.profile_context_audit_events(user_id, profile_id, revision);

alter table public.profile_context_ledgers enable row level security;
alter table public.profile_context_facts enable row level security;
alter table public.profile_context_mutations enable row level security;
alter table public.profile_context_audit_events enable row level security;

do $$
declare
  t text;
  r text;
  tables text[] := array[
    'profile_context_ledgers', 'profile_context_facts',
    'profile_context_mutations', 'profile_context_audit_events'
  ];
  backend_roles text[] := array['postgres', 'service_role'];
begin
  foreach t in array tables loop
    execute format(
      'create policy %I on public.%I for all using (user_id = auth.uid()::text) with check (user_id = auth.uid()::text)',
      'Users manage own ' || t, t
    );
    foreach r in array backend_roles loop
      if exists (select 1 from pg_roles where rolname = r) then
        execute format(
          'create policy %I on public.%I for all to %I using (true) with check (true)',
          'Backend role full access ' || r, t, r
        );
        execute format('grant select, insert, update, delete on public.%I to %I', t, r);
      end if;
    end loop;
    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute format('revoke all on public.%I from anon', t);
    end if;
    -- Authenticated clients use FastAPI. Direct grants would bypass optimistic
    -- revisions, idempotency, consent validation, and deletion scrubbing.
    if exists (select 1 from pg_roles where rolname = 'authenticated') then
      execute format('revoke all on public.%I from authenticated', t);
    end if;
  end loop;
end $$;
