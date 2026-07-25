-- =====================================================================
-- Fix RLS on the legacy tables + authorise the backend role
--
-- Context
--   The four original tables (kundlis, readings, prediction_claims,
--   user_settings) were created by SQLAlchemy `Base.metadata.create_all()`,
--   not by docs/supabase_schema.sql. Proof: applying the previous
--   migration reported `constraint "user_settings_chart_style_check" ...
--   does not exist, skipping`. create_all() does not create CHECK
--   constraints, RLS, or policies — so RLS was never enabled on the
--   tables holding every user's birth date, time and place, while the
--   Angular app ships @supabase/supabase-js (anon key reaches the browser).
--
-- Why this needs more than "enable row level security"
--   The FastAPI backend connects over the Supabase pooler as the
--   `postgres` role using DATABASE_URL (see docs/deploy_gcp.md), NOT as
--   `service_role`, and NOT through PostgREST. In that connection
--   `auth.uid()` is NULL, so a policy of `user_id = auth.uid()::text`
--   matches zero rows. Enabling RLS without authorising that role would
--   return empty results for every backend query.
--
--   Postgres does exempt a table's OWNER from RLS, and these tables are
--   owned by `postgres`, so owner-bypass alone would probably carry the
--   backend. This migration does not rely on that: it adds an explicit
--   permissive policy for the backend roles so behaviour is the same
--   whether or not ownership ever changes. Permissive policies are OR-ed,
--   so this widens access for the backend without weakening the
--   per-user rules for everyone else.
--
--   FORCE ROW LEVEL SECURITY is deliberately NOT set, which keeps
--   owner-bypass available as a second safety net.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Enable RLS on the four legacy tables
-- ---------------------------------------------------------------------

alter table public.kundlis            enable row level security;
alter table public.readings           enable row level security;
alter table public.prediction_claims  enable row level security;
alter table public.user_settings      enable row level security;


-- ---------------------------------------------------------------------
-- 2. Per-user ownership policies for the legacy tables
--    (what docs/supabase_schema.sql intended but never applied)
-- ---------------------------------------------------------------------

do $$
begin
  -- kundlis: direct ownership
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='kundlis' and policyname='Users manage own kundlis') then
    create policy "Users manage own kundlis" on public.kundlis for all
      using (user_id = auth.uid()::text)
      with check (user_id = auth.uid()::text);
  end if;

  -- user_settings: direct ownership
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='user_settings' and policyname='Users manage own settings') then
    create policy "Users manage own settings" on public.user_settings for all
      using (user_id = auth.uid()::text)
      with check (user_id = auth.uid()::text);
  end if;

  -- prediction_claims: direct ownership
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='prediction_claims' and policyname='Users manage own prediction claims') then
    create policy "Users manage own prediction claims" on public.prediction_claims for all
      using (user_id = auth.uid()::text)
      with check (user_id = auth.uid()::text);
  end if;

  -- readings: ownership inherited through the parent kundli
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='readings' and policyname='Users manage own readings') then
    create policy "Users manage own readings" on public.readings for all
      using (exists (
        select 1 from public.kundlis k
        where k.id = readings.kundli_id and k.user_id = auth.uid()::text))
      with check (exists (
        select 1 from public.kundlis k
        where k.id = readings.kundli_id and k.user_id = auth.uid()::text));
  end if;
end $$;


-- ---------------------------------------------------------------------
-- 3. Authorise the backend roles on every application table
--
--    `postgres`     — how the FastAPI backend connects via the pooler.
--    `service_role` — used by server-side Supabase clients / edge
--                     functions; already bypasses RLS, included so the
--                     grant is explicit rather than implicit.
--
--    The backend performs its own ownership checks in
--    astrospace/api/auth.py (Supabase bearer token -> user id), so a
--    permissive policy here does not remove an authorisation layer; it
--    keeps the one that already exists.
-- ---------------------------------------------------------------------

do $$
declare
  t text;
  r text;
  app_tables text[] := array[
    -- legacy
    'kundlis', 'readings', 'prediction_claims', 'user_settings',
    -- mobile app schema (20260725120000)
    'user_profiles', 'user_devices', 'ask_threads', 'ask_messages',
    'user_remedies', 'remedy_completions', 'muhurta_requests', 'saved_muhurtas',
    'user_observances', 'compatibility_checks', 'push_tokens',
    'notification_preferences', 'notification_jobs', 'notification_deliveries',
    'user_alerts', 'widget_installs', 'live_activities',
    'daily_guidance_cache', 'audio_renders', 'share_assets',
    -- catalogs (write access for the ingestion/seed jobs)
    'remedies', 'muhurta_goals', 'festivals', 'festival_occurrences',
    'glossary_terms'
  ];
  backend_roles text[] := array['postgres', 'service_role'];
begin
  foreach t in array app_tables loop
    -- skip anything not present, so this migration stays re-runnable
    if not exists (
      select 1 from pg_tables where schemaname = 'public' and tablename = t
    ) then
      continue;
    end if;

    foreach r in array backend_roles loop
      if not exists (select 1 from pg_roles where rolname = r) then
        continue;
      end if;

      if not exists (
        select 1 from pg_policies
        where schemaname = 'public' and tablename = t
          and policyname = 'Backend role full access ' || r
      ) then
        execute format(
          'create policy %I on public.%I for all to %I using (true) with check (true)',
          'Backend role full access ' || r, t, r);
      end if;
    end loop;
  end loop;
end $$;


-- ---------------------------------------------------------------------
-- 4. Least privilege for the browser anon role
--
--    The Angular app uses supabase-js for AUTH ONLY — all data goes
--    through FastAPI. Unauthenticated visitors therefore never need
--    table access. RLS already yields zero rows for them (no anon
--    policy exists); revoking the grants removes the reliance on RLS
--    being correctly configured for that to hold.
--
--    To undo:
--      grant select, insert, update, delete on public.<table> to anon;
-- ---------------------------------------------------------------------

do $$
declare
  t text;
  personal_tables text[] := array[
    'kundlis', 'readings', 'prediction_claims', 'user_settings',
    'user_profiles', 'user_devices', 'ask_threads', 'ask_messages',
    'user_remedies', 'remedy_completions', 'muhurta_requests', 'saved_muhurtas',
    'user_observances', 'compatibility_checks', 'push_tokens',
    'notification_preferences', 'notification_jobs', 'notification_deliveries',
    'user_alerts', 'widget_installs', 'live_activities',
    'daily_guidance_cache', 'share_assets'
  ];
begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    return;
  end if;

  foreach t in array personal_tables loop
    if exists (select 1 from pg_tables where schemaname='public' and tablename=t) then
      execute format('revoke all on public.%I from anon', t);
    end if;
  end loop;
end $$;
