-- =====================================================================
-- AstroSpace — mobile app schema
-- Backs the 70 designed screens in "Mobile App UI Screens/".
--
-- Conventions follow the newer migrations in this folder (uuid PKs,
-- text columns, timestamptz) rather than the legacy varchar/timestamp
-- style in docs/supabase_schema.sql. Foreign keys into the legacy
-- kundlis/readings tables use text, which Postgres coerces to varchar.
--
-- Sections
--   1. Fixes + additions to existing tables
--   2. User profile & devices
--   3. Ask (conversational surface)
--   4. Remedies & muhurta ("what to do" layer)
--   5. Festivals & observances
--   6. Compatibility / matchmaking
--   7. Notifications & alerts
--   8. Native surfaces (widgets, live activities)
--   9. Caches (daily guidance, audio, share assets)
--  10. Glossary / learning layer
--  11. Row-level security
--  12. updated_at triggers
-- =====================================================================

-- ---------------------------------------------------------------------
-- 0. Shared helper
-- ---------------------------------------------------------------------

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;


-- ---------------------------------------------------------------------
-- 1. Fixes + additions to existing tables
-- ---------------------------------------------------------------------

-- 1a. chart_style must allow 'eastern' — the mobile app defaults to it.
--     The original constraint only permitted ('south','north').
alter table public.user_settings
  drop constraint if exists user_settings_chart_style_check;

alter table public.user_settings
  add constraint user_settings_chart_style_check
  check (chart_style in ('south', 'north', 'eastern'));

alter table public.user_settings
  alter column chart_style set default 'eastern';

-- 1b. Experience mode + fear-handling tone. These drive labels, nav
--     priority, default disclosure and copy register app-wide, and are
--     the backbone of the Guided/Balanced/Practitioner design.
alter table public.user_settings
  add column if not exists experience_mode text not null default 'balanced',
  add column if not exists tone text not null default 'gentle',
  add column if not exists large_tap_mode boolean not null default false,
  add column if not exists audio_enabled boolean not null default true,
  add column if not exists reduce_motion boolean not null default false,
  add column if not exists onboarding_completed_at timestamptz;

alter table public.user_settings
  drop constraint if exists user_settings_experience_mode_check;
alter table public.user_settings
  add constraint user_settings_experience_mode_check
  check (experience_mode in ('guided', 'balanced', 'practitioner'));

alter table public.user_settings
  drop constraint if exists user_settings_tone_check;
alter table public.user_settings
  add constraint user_settings_tone_check
  check (tone in ('gentle', 'direct'));

-- 1c. Persist resolved coordinates + timezone on kundlis. Required for
--     timezone-correct panchang/muhurta for the diaspora segment; today
--     only birth_city/birth_nation are stored and coords are re-resolved
--     at runtime.
alter table public.kundlis
  add column if not exists birth_latitude double precision,
  add column if not exists birth_longitude double precision,
  add column if not exists birth_timezone text,
  add column if not exists birth_state text,
  add column if not exists birth_time_accuracy text not null default 'exact',
  add column if not exists kind text not null default 'profile',
  add column if not exists archived_at timestamptz;

alter table public.kundlis
  drop constraint if exists kundlis_birth_time_accuracy_check;
alter table public.kundlis
  add constraint kundlis_birth_time_accuracy_check
  check (birth_time_accuracy in ('exact', 'approximate', 'unknown'));

-- 'prospect' = lightweight chart added only for a compatibility check;
-- excluded from the profile switcher.
alter table public.kundlis
  drop constraint if exists kundlis_kind_check;
alter table public.kundlis
  add constraint kundlis_kind_check
  check (kind in ('profile', 'prospect'));

-- 1d. Readings gain a language so Telugu output is addressable.
alter table public.readings
  add column if not exists language text not null default 'en';


-- ---------------------------------------------------------------------
-- 2. User profile & devices
-- ---------------------------------------------------------------------

create table if not exists public.user_profiles (
  user_id text primary key,
  display_name text,
  avatar_url text,
  locale text not null default 'en',
  timezone text,
  marketing_opt_in boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.user_devices (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  device_id text not null,
  platform text not null check (platform in ('ios', 'android', 'web')),
  model text,
  os_version text,
  app_version text,
  locale text,
  timezone text,
  last_seen_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  unique (user_id, device_id)
);

create index if not exists idx_user_devices_user on public.user_devices(user_id);


-- ---------------------------------------------------------------------
-- 3. Ask — conversational surface (M3)
-- ---------------------------------------------------------------------

create table if not exists public.ask_threads (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  kundli_id text not null references public.kundlis(id) on delete cascade,
  title text,
  last_message_at timestamptz,
  message_count integer not null default 0,
  archived_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.ask_messages (
  id uuid primary key default gen_random_uuid(),
  thread_id uuid not null references public.ask_threads(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  -- CE routing + evidence shown behind "Why this?"
  domain text,
  evidence jsonb not null default '{}'::jsonb,
  -- when non-null the answer was a refer-out, not a prediction
  refer_out_kind text check (refer_out_kind in ('medical', 'legal', 'financial', 'longevity', 'emergency')),
  input_mode text not null default 'text' check (input_mode in ('text', 'voice', 'chip')),
  language text not null default 'en',
  model text,
  latency_ms integer,
  created_at timestamptz not null default now()
);

create index if not exists idx_ask_threads_user_kundli
  on public.ask_threads(user_id, kundli_id, last_message_at desc);
create index if not exists idx_ask_messages_thread
  on public.ask_messages(thread_id, created_at);


-- ---------------------------------------------------------------------
-- 4. Remedies & muhurta — the "what to do" layer (M7)
-- ---------------------------------------------------------------------

-- Catalog. Public read; curated by the team, not user-writable.
create table if not exists public.remedies (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  title text not null,
  remedy_type text not null
    check (remedy_type in ('mantra', 'gem', 'vrat', 'donation', 'colour', 'deity', 'practice')),
  instructions text not null,
  -- what this remedy addresses, e.g. {"dosha":"manglik"} / {"planet":"saturn"}
  applies_to jsonb not null default '{}'::jsonb,
  tradition_source text,
  default_target_count integer,
  cadence text check (cadence in ('daily', 'weekly', 'monthly', 'once')),
  is_convention_dependent boolean not null default true,
  language text not null default 'en',
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.user_remedies (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  kundli_id text not null references public.kundlis(id) on delete cascade,
  remedy_id uuid not null references public.remedies(id) on delete restrict,
  status text not null default 'active'
    check (status in ('active', 'paused', 'completed', 'abandoned')),
  target_count integer,
  cadence text check (cadence in ('daily', 'weekly', 'monthly', 'once')),
  reminder_enabled boolean not null default false,
  reminder_time time,
  reminder_weekday smallint check (reminder_weekday between 0 and 6),
  timezone text,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- One row per day the practice was done; streaks are derived from this.
create table if not exists public.remedy_completions (
  id uuid primary key default gen_random_uuid(),
  user_remedy_id uuid not null references public.user_remedies(id) on delete cascade,
  occurred_on date not null,
  count integer not null default 1,
  created_at timestamptz not null default now(),
  unique (user_remedy_id, occurred_on)
);

create index if not exists idx_user_remedies_user_kundli
  on public.user_remedies(user_id, kundli_id, status);
create index if not exists idx_remedy_completions_lookup
  on public.remedy_completions(user_remedy_id, occurred_on desc);

-- Goal catalog for the muhurta finder.
create table if not exists public.muhurta_goals (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  label text not null,
  description text,
  rules jsonb not null default '{}'::jsonb,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.muhurta_requests (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  kundli_id text not null references public.kundlis(id) on delete cascade,
  goal_slug text not null,
  free_text_goal text,
  date_from date not null,
  date_to date not null,
  place jsonb not null default '{}'::jsonb,
  status text not null default 'pending'
    check (status in ('pending', 'ready', 'empty', 'failed')),
  results jsonb not null default '[]'::jsonb,
  computed_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.saved_muhurtas (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  kundli_id text not null references public.kundlis(id) on delete cascade,
  request_id uuid references public.muhurta_requests(id) on delete set null,
  goal_slug text,
  label text,
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  quality text check (quality in ('best', 'good', 'workable')),
  why jsonb not null default '{}'::jsonb,
  device_calendar_event_id text,
  created_at timestamptz not null default now()
);

create index if not exists idx_muhurta_requests_user
  on public.muhurta_requests(user_id, kundli_id, created_at desc);
create index if not exists idx_saved_muhurtas_user_start
  on public.saved_muhurtas(user_id, starts_at);


-- ---------------------------------------------------------------------
-- 5. Festivals & observances (M6)
-- ---------------------------------------------------------------------

create table if not exists public.festivals (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  name_local text,
  language text not null default 'en',
  region text,
  tradition text,
  description text,
  prep_guidance text,
  -- panchanga rule used to compute the date, e.g.
  -- {"masa":"shravana","tithi":"panchami","paksha":"shukla"}
  panchanga_rule jsonb not null default '{}'::jsonb,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Resolved dates. place_key lets the same festival land on different
-- days for different locations (the diaspora case).
create table if not exists public.festival_occurrences (
  id uuid primary key default gen_random_uuid(),
  festival_id uuid not null references public.festivals(id) on delete cascade,
  occurs_on date not null,
  place_key text not null default 'default',
  starts_at timestamptz,
  ends_at timestamptz,
  best_window jsonb,
  computed_meta jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (festival_id, occurs_on, place_key)
);

create table if not exists public.user_observances (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  kundli_id text references public.kundlis(id) on delete cascade,
  festival_id uuid not null references public.festivals(id) on delete cascade,
  occurs_on date not null,
  status text not null default 'planned'
    check (status in ('planned', 'observed', 'skipped')),
  reminder_enabled boolean not null default false,
  reminder_lead_days smallint not null default 2,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, festival_id, occurs_on)
);

create index if not exists idx_festival_occurrences_date
  on public.festival_occurrences(occurs_on, place_key);
create index if not exists idx_user_observances_user_date
  on public.user_observances(user_id, occurs_on);


-- ---------------------------------------------------------------------
-- 6. Compatibility / matchmaking (M8)
-- ---------------------------------------------------------------------

create table if not exists public.compatibility_checks (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  kundli_id text not null references public.kundlis(id) on delete cascade,
  partner_kundli_id text not null references public.kundlis(id) on delete cascade,
  total_score numeric(4,1),
  max_score numeric(4,1) not null default 36,
  koota_breakdown jsonb not null default '{}'::jsonb,
  dosha_flags jsonb not null default '{}'::jsonb,
  verdict text,
  conventions jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_compatibility_user
  on public.compatibility_checks(user_id, created_at desc);


-- ---------------------------------------------------------------------
-- 7. Notifications & alerts
--    push_tokens      -> where to send
--    notification_preferences -> whether the user wants it
--    notification_jobs        -> what is scheduled
--    notification_deliveries  -> per-token send receipts
--    user_alerts              -> the in-app inbox
-- ---------------------------------------------------------------------

create table if not exists public.push_tokens (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  device_id uuid references public.user_devices(id) on delete cascade,
  provider text not null check (provider in ('apns', 'fcm', 'webpush')),
  token text not null,
  environment text not null default 'production'
    check (environment in ('production', 'sandbox')),
  locale text,
  timezone text,
  last_seen_at timestamptz not null default now(),
  revoked_at timestamptz,
  created_at timestamptz not null default now(),
  unique (provider, token)
);

create index if not exists idx_push_tokens_user_active
  on public.push_tokens(user_id) where revoked_at is null;

-- One row per user per category. Categories mirror the Settings screen.
create table if not exists public.notification_preferences (
  user_id text not null,
  category text not null check (category in (
    'morning_brief',      -- "Your day, Lakshmi"
    'window_alert',       -- Rahu Kalam / auspicious window starting
    'festival_reminder',  -- observance prep, N days ahead
    'remedy_reminder',    -- streak / scheduled practice
    'muhurta_reminder',   -- a saved muhurta is approaching
    'reading_ready',      -- generated reading finished
    'accuracy_review',    -- a prediction claim is ready to validate
    'match_report_ready', -- compatibility report finished
    'system'              -- transactional / account
  )),
  enabled boolean not null default true,
  channels text[] not null default array['push','in_app'],
  -- window_alert: how long before the window to notify
  lead_time_minutes integer,
  -- festival_reminder: how many days ahead
  lead_time_days smallint,
  -- preferred send time for digest-style categories
  preferred_time time,
  quiet_hours_start time,
  quiet_hours_end time,
  timezone text,
  updated_at timestamptz not null default now(),
  primary key (user_id, category)
);

create table if not exists public.notification_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  kundli_id text references public.kundlis(id) on delete cascade,
  category text not null,
  -- prevents duplicate sends, e.g. 'morning_brief:<kundli>:2026-07-25'
  dedupe_key text unique,
  scheduled_for timestamptz not null,
  timezone text,
  title text not null,
  body text,
  deep_link text,
  payload jsonb not null default '{}'::jsonb,
  language text not null default 'en',
  status text not null default 'pending'
    check (status in ('pending', 'processing', 'sent', 'failed', 'cancelled', 'skipped')),
  skip_reason text,
  attempts smallint not null default 0,
  last_error text,
  sent_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_notification_jobs_due
  on public.notification_jobs(scheduled_for)
  where status = 'pending';
create index if not exists idx_notification_jobs_user
  on public.notification_jobs(user_id, created_at desc);

create table if not exists public.notification_deliveries (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.notification_jobs(id) on delete cascade,
  push_token_id uuid references public.push_tokens(id) on delete set null,
  provider text,
  provider_message_id text,
  status text not null default 'queued'
    check (status in ('queued', 'sent', 'delivered', 'failed', 'opened', 'dismissed')),
  status_at timestamptz not null default now(),
  error text,
  receipt jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_notification_deliveries_job
  on public.notification_deliveries(job_id);

-- In-app alert inbox. Deliberately has no 'critical'/'danger' severity —
-- the product never uses fear framing (design_principles.md §4).
create table if not exists public.user_alerts (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  kundli_id text references public.kundlis(id) on delete cascade,
  category text not null,
  severity text not null default 'info'
    check (severity in ('info', 'attention')),
  title text not null,
  body text,
  deep_link text,
  source_job_id uuid references public.notification_jobs(id) on delete set null,
  read_at timestamptz,
  dismissed_at timestamptz,
  expires_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists idx_user_alerts_unread
  on public.user_alerts(user_id, created_at desc)
  where read_at is null and dismissed_at is null;


-- ---------------------------------------------------------------------
-- 8. Native surfaces (M10)
-- ---------------------------------------------------------------------

create table if not exists public.widget_installs (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  device_id uuid references public.user_devices(id) on delete cascade,
  kind text not null check (kind in (
    'day_quality', 'next_window', 'panchang', 'remedy_of_day', 'festival_countdown'
  )),
  family text check (family in ('small', 'medium', 'large', 'circular', 'rectangular', 'inline')),
  kundli_id text references public.kundlis(id) on delete cascade,
  settings jsonb not null default '{}'::jsonb,
  last_rendered_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.live_activities (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  device_id uuid references public.user_devices(id) on delete cascade,
  kundli_id text references public.kundlis(id) on delete cascade,
  kind text not null check (kind in ('window_countdown', 'muhurta', 'remedy_timer', 'vrat')),
  activity_token text,
  push_to_start_token text,
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  state jsonb not null default '{}'::jsonb,
  status text not null default 'active'
    check (status in ('active', 'ended', 'dismissed', 'stale')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_live_activities_active
  on public.live_activities(user_id, ends_at)
  where status = 'active';


-- ---------------------------------------------------------------------
-- 9. Caches — offline Today, TTS audio, share assets
-- ---------------------------------------------------------------------

-- Supports the offline-first daily card. conventions_hash keys the row to
-- the ayanamsha/node/place used, so changing a convention invalidates it.
create table if not exists public.daily_guidance_cache (
  id uuid primary key default gen_random_uuid(),
  kundli_id text not null references public.kundlis(id) on delete cascade,
  local_date date not null,
  conventions_hash text not null,
  place jsonb not null default '{}'::jsonb,
  payload jsonb not null,
  language text not null default 'en',
  computed_at timestamptz not null default now(),
  expires_at timestamptz,
  unique (kundli_id, local_date, conventions_hash, language)
);

create table if not exists public.audio_renders (
  id uuid primary key default gen_random_uuid(),
  user_id text,
  kundli_id text references public.kundlis(id) on delete cascade,
  source_kind text not null
    check (source_kind in ('daily_guidance', 'ask_answer', 'remedy', 'reading', 'festival')),
  source_id text,
  text_sha256 text not null,
  language text not null default 'en',
  voice text,
  tone text check (tone in ('gentle', 'direct')),
  storage_bucket text,
  storage_path text,
  duration_ms integer,
  status text not null default 'ready'
    check (status in ('pending', 'ready', 'failed')),
  created_at timestamptz not null default now(),
  expires_at timestamptz,
  unique (text_sha256, language, voice)
);

create table if not exists public.share_assets (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  kundli_id text references public.kundlis(id) on delete cascade,
  kind text not null
    check (kind in ('daily_card', 'match_report', 'why_this_reading', 'reading')),
  payload jsonb not null default '{}'::jsonb,
  storage_bucket text,
  storage_path text,
  share_token text unique,
  is_public boolean not null default false,
  expires_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists idx_daily_cache_lookup
  on public.daily_guidance_cache(kundli_id, local_date desc);


-- ---------------------------------------------------------------------
-- 10. Glossary / learning layer (M4f)
-- ---------------------------------------------------------------------

create table if not exists public.glossary_terms (
  id uuid primary key default gen_random_uuid(),
  slug text not null,
  language text not null default 'en',
  term text not null,
  category text check (category in (
    'yoga', 'dosha', 'dasha', 'nakshatra', 'graha', 'house', 'varga', 'panchanga', 'general'
  )),
  plain_definition text not null,
  classical_rule text,
  source_citation text,
  verse text,
  is_convention_dependent boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (slug, language)
);


-- ---------------------------------------------------------------------
-- 11. Row-level security
-- ---------------------------------------------------------------------

-- 11a. User-owned tables: simple user_id = auth.uid() ownership.
do $$
declare
  t text;
  user_owned text[] := array[
    'user_profiles', 'user_devices', 'ask_threads', 'user_remedies',
    'muhurta_requests', 'saved_muhurtas', 'user_observances',
    'compatibility_checks', 'push_tokens', 'notification_preferences',
    'notification_jobs', 'user_alerts', 'widget_installs',
    'live_activities', 'share_assets'
  ];
begin
  foreach t in array user_owned loop
    execute format('alter table public.%I enable row level security', t);

    if not exists (
      select 1 from pg_policies
      where schemaname = 'public' and tablename = t and policyname = 'Users read own rows'
    ) then
      execute format(
        'create policy "Users read own rows" on public.%I for select using (user_id = auth.uid()::text)', t);
    end if;

    if not exists (
      select 1 from pg_policies
      where schemaname = 'public' and tablename = t and policyname = 'Users manage own rows'
    ) then
      execute format(
        'create policy "Users manage own rows" on public.%I for all
           using (user_id = auth.uid()::text)
           with check (user_id = auth.uid()::text)', t);
    end if;
  end loop;
end $$;

-- 11b. Child tables: ownership is inherited through the parent.
alter table public.ask_messages enable row level security;
alter table public.remedy_completions enable row level security;
alter table public.notification_deliveries enable row level security;
alter table public.daily_guidance_cache enable row level security;
alter table public.audio_renders enable row level security;

do $$
begin
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='ask_messages' and policyname='Users access own thread messages') then
    create policy "Users access own thread messages" on public.ask_messages for all
      using (exists (select 1 from public.ask_threads t
                     where t.id = ask_messages.thread_id and t.user_id = auth.uid()::text))
      with check (exists (select 1 from public.ask_threads t
                     where t.id = ask_messages.thread_id and t.user_id = auth.uid()::text));
  end if;

  if not exists (select 1 from pg_policies where schemaname='public' and tablename='remedy_completions' and policyname='Users access own remedy completions') then
    create policy "Users access own remedy completions" on public.remedy_completions for all
      using (exists (select 1 from public.user_remedies r
                     where r.id = remedy_completions.user_remedy_id and r.user_id = auth.uid()::text))
      with check (exists (select 1 from public.user_remedies r
                     where r.id = remedy_completions.user_remedy_id and r.user_id = auth.uid()::text));
  end if;

  if not exists (select 1 from pg_policies where schemaname='public' and tablename='notification_deliveries' and policyname='Users read own deliveries') then
    create policy "Users read own deliveries" on public.notification_deliveries for select
      using (exists (select 1 from public.notification_jobs j
                     where j.id = notification_deliveries.job_id and j.user_id = auth.uid()::text));
  end if;

  if not exists (select 1 from pg_policies where schemaname='public' and tablename='daily_guidance_cache' and policyname='Users access own daily cache') then
    create policy "Users access own daily cache" on public.daily_guidance_cache for all
      using (exists (select 1 from public.kundlis k
                     where k.id = daily_guidance_cache.kundli_id and k.user_id = auth.uid()::text))
      with check (exists (select 1 from public.kundlis k
                     where k.id = daily_guidance_cache.kundli_id and k.user_id = auth.uid()::text));
  end if;

  if not exists (select 1 from pg_policies where schemaname='public' and tablename='audio_renders' and policyname='Users read audio renders') then
    -- audio is content-addressed and shareable across users by text hash
    create policy "Users read audio renders" on public.audio_renders for select using (true);
  end if;
end $$;

-- 11c. Catalog tables: readable by everyone, writable only by the
--      service role (which bypasses RLS).
do $$
declare
  t text;
  catalogs text[] := array[
    'remedies', 'muhurta_goals', 'festivals', 'festival_occurrences', 'glossary_terms'
  ];
begin
  foreach t in array catalogs loop
    execute format('alter table public.%I enable row level security', t);
    if not exists (
      select 1 from pg_policies
      where schemaname = 'public' and tablename = t and policyname = 'Catalog is readable'
    ) then
      execute format('create policy "Catalog is readable" on public.%I for select using (true)', t);
    end if;
  end loop;
end $$;


-- ---------------------------------------------------------------------
-- 12. updated_at triggers
-- ---------------------------------------------------------------------

do $$
declare
  t text;
  touched text[] := array[
    'user_profiles', 'ask_threads', 'remedies', 'user_remedies', 'festivals',
    'user_observances', 'notification_jobs', 'live_activities', 'glossary_terms'
  ];
begin
  foreach t in array touched loop
    execute format('drop trigger if exists set_updated_at on public.%I', t);
    execute format(
      'create trigger set_updated_at before update on public.%I
       for each row execute function public.set_updated_at()', t);
  end loop;
end $$;
