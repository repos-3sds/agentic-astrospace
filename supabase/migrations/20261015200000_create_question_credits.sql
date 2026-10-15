-- D2 hybrid pricing: question packs are non-expiring Ask credits held per
-- verified store transaction. Monthly allowances stay in usage_buckets.

create table if not exists public.question_credits (
  id uuid primary key default gen_random_uuid(),
  billing_account_id uuid not null references public.billing_accounts(id) on delete cascade,
  provider text not null,
  provider_product_id text not null,
  provider_transaction_id text not null,
  quantity integer not null check (quantity > 0),
  remaining integer not null,
  revoked_at timestamptz,
  created_at timestamptz not null default now(),
  unique(provider, provider_transaction_id),
  check (remaining >= 0 and remaining <= quantity)
);

create index if not exists idx_question_credits_account
  on public.question_credits(billing_account_id, created_at);

alter table public.question_credits enable row level security;

-- Same rule as the rest of the commercial foundation: only the backend
-- touches these rows; clients see a resolved snapshot.
do $$
declare
  r text;
begin
  foreach r in array array['postgres', 'service_role'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      execute format(
        'create policy %I on public.question_credits for all to %I using (true) with check (true)',
        'Backend role full access ' || r, r
      );
      execute format('grant select, insert, update, delete on public.question_credits to %I', r);
    end if;
  end loop;
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on public.question_credits from anon;
  end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    revoke all on public.question_credits from authenticated;
  end if;
end $$;
