-- Status: canonical (CI fixture). The parts of a Supabase database the
-- migrations in supabase/migrations/ lean on, for a plain pgvector Postgres
-- in CI (audit I12). Not a copy of Supabase: only what the migrations name.
-- Production is never touched by this file.

do $$ begin
  create role anon nologin;
exception when duplicate_object then null; end $$;
do $$ begin
  create role authenticated nologin;
exception when duplicate_object then null; end $$;
do $$ begin
  create role service_role nologin bypassrls;
exception when duplicate_object then null; end $$;

create schema if not exists extensions;
create schema if not exists auth;
create schema if not exists storage;

create table if not exists auth.users (
  id uuid primary key,
  email text,
  created_at timestamptz default now()
);

-- Supabase reads the caller's id from the request's JWT claims.
create or replace function auth.uid() returns uuid
language sql stable as $$
  select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;

create table if not exists storage.buckets (
  id text primary key,
  name text not null,
  owner uuid,
  public boolean default false,
  file_size_limit bigint,
  allowed_mime_types text[],
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists storage.objects (
  id uuid primary key default gen_random_uuid(),
  bucket_id text references storage.buckets (id),
  name text,
  owner uuid,
  metadata jsonb,
  created_at timestamptz default now()
);
alter table storage.objects enable row level security;

grant usage on schema auth, storage, extensions to anon, authenticated, service_role;

-- Made in the live project from the dashboard, never by a migration;
-- 20261017183842 revokes it. In production it is the event trigger that turns
-- RLS on for new tables; here a stub is enough for the REVOKE to apply.
create or replace function public.rls_auto_enable() returns void
language sql as $$ select $$;
