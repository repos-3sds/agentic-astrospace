-- Prompt readers on an old build of the app to update (docs/app_updates.md).
--
-- app_releases: one row per platform. latest_build is the build readers can
-- install now (Android: the one on closed testing, set by Announce; iOS: the
-- one in TestFlight's tester group, set by the App versions workflow).
-- required_build, when set, is the oldest build still allowed to open: any
-- older build shows a full-screen "please update" and nothing else.
-- block_after_days, when set, does the same for every build below
-- latest_build once that many days have passed since it was set.
--
-- push_tokens.app_build: the build the phone was running when it last
-- registered its token, sent by the app on every launch. Builds from before
-- this send nothing, which the worker reads as "older than this feature".
--
-- Only the API and the notifications worker read and write app_releases, as
-- the backend role. RLS on with no policy and both client roles lose every
-- grant (the 2026-10-18 audit's S2/S21 rule for new tables).
create table if not exists public.app_releases (
  platform text primary key check (platform in ('android', 'ios')),
  latest_build integer check (latest_build is null or latest_build > 0),
  latest_set_at timestamptz,
  required_build integer check (required_build is null or required_build > 0),
  block_after_days integer check (block_after_days is null or block_after_days >= 0),
  update_url text,
  updated_by text,
  updated_at timestamptz not null default now()
);

alter table public.app_releases enable row level security;

do $$
declare
  r text;
begin
  foreach r in array array['authenticated', 'anon'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      execute format('revoke all on public.app_releases from %I', r);
    end if;
  end loop;
end $$;

alter table public.push_tokens add column if not exists app_build integer;
