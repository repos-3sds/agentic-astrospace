-- CE-2: server-authoritative entitlement vocabulary and persistence.
-- This migration does not activate products, prices, purchases, or quotas.

create table if not exists public.billing_accounts (
  id uuid primary key default gen_random_uuid(),
  owner_user_id text not null,
  kind text not null default 'individual' check (kind in ('individual', 'family')),
  entitlement_revision integer not null default 0 check (entitlement_revision >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(owner_user_id, kind)
);

create table if not exists public.subscription_grants (
  id uuid primary key default gen_random_uuid(),
  billing_account_id uuid not null references public.billing_accounts(id) on delete cascade,
  provider text not null,
  provider_product_id text not null,
  provider_transaction_id text not null,
  state text not null default 'pending'
    check (state in ('pending', 'active', 'grace', 'paused', 'expired', 'revoked')),
  starts_at timestamptz,
  renews_at timestamptz,
  expires_at timestamptz,
  grace_ends_at timestamptz,
  verified_at timestamptz,
  last_event_at timestamptz,
  provider_reference_hash text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(provider, provider_transaction_id)
);

create index if not exists idx_subscription_grants_account
  on public.subscription_grants(billing_account_id, state);

create table if not exists public.plan_assignments (
  id uuid primary key default gen_random_uuid(),
  billing_account_id uuid not null references public.billing_accounts(id) on delete cascade,
  access_tier text not null check (access_tier in ('free', 'plus', 'pro')),
  account_topology text not null check (account_topology in ('individual', 'family')),
  offer_code text,
  source_grant_id uuid references public.subscription_grants(id) on delete set null,
  effective_at timestamptz not null,
  ends_at timestamptz,
  revision integer not null check (revision >= 0),
  created_at timestamptz not null default now(),
  unique(billing_account_id, revision),
  check (ends_at is null or ends_at > effective_at)
);

create table if not exists public.entitlement_overrides (
  id uuid primary key default gen_random_uuid(),
  billing_account_id uuid not null references public.billing_accounts(id) on delete cascade,
  entitlement_key text not null,
  value jsonb not null,
  reason text not null,
  actor_user_id text not null,
  revision integer not null check (revision > 0),
  effective_at timestamptz not null,
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  check (expires_at is null or expires_at > effective_at),
  unique(billing_account_id, revision)
);

create index if not exists idx_entitlement_overrides_account_key
  on public.entitlement_overrides(billing_account_id, entitlement_key);

create table if not exists public.usage_buckets (
  id uuid primary key default gen_random_uuid(),
  billing_account_id uuid not null references public.billing_accounts(id) on delete cascade,
  scope_id text not null default 'account',
  entitlement_key text not null,
  period_id text not null,
  period_start timestamptz not null,
  period_end timestamptz not null,
  reserved integer not null default 0 check (reserved >= 0),
  consumed integer not null default 0 check (consumed >= 0),
  version integer not null default 0 check (version >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(billing_account_id, scope_id, entitlement_key, period_id),
  check (period_end > period_start)
);

create table if not exists public.entitlement_audit_events (
  id uuid primary key default gen_random_uuid(),
  billing_account_id uuid references public.billing_accounts(id) on delete set null,
  user_id text not null,
  action text not null,
  entitlement_key text,
  detail jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_entitlement_audit_user_created
  on public.entitlement_audit_events(user_id, created_at desc);

alter table public.billing_accounts enable row level security;
alter table public.subscription_grants enable row level security;
alter table public.plan_assignments enable row level security;
alter table public.entitlement_overrides enable row level security;
alter table public.usage_buckets enable row level security;
alter table public.entitlement_audit_events enable row level security;

-- All commercial records flow through FastAPI. Native/web clients receive a
-- resolved snapshot and never direct table access, receipt tokens, or grants.
do $$
declare
  t text;
  r text;
  tables text[] := array[
    'billing_accounts', 'subscription_grants', 'plan_assignments',
    'entitlement_overrides', 'usage_buckets', 'entitlement_audit_events'
  ];
  backend_roles text[] := array['postgres', 'service_role'];
begin
  foreach t in array tables loop
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
    if exists (select 1 from pg_roles where rolname = 'authenticated') then
      execute format('revoke all on public.%I from authenticated', t);
    end if;
  end loop;
end $$;
