-- AstroSpace Supabase/Postgres schema
-- Run this in Supabase SQL Editor before pointing DATABASE_URL at Supabase Postgres.
-- The FastAPI backend enforces auth ownership using the Supabase bearer token.

create table if not exists public.kundlis (
  id varchar primary key,
  user_id varchar not null default 'local-dev-user',
  name varchar not null,
  relation varchar not null default 'friend',
  birth_year integer not null,
  birth_month integer not null,
  birth_day integer not null,
  birth_hour integer not null default 12,
  birth_minute integer not null default 0,
  birth_city varchar not null,
  birth_nation varchar not null default 'US',
  sun_sign varchar,
  moon_sign varchar,
  ascendant varchar,
  chart_data jsonb,
  notes text,
  created_at timestamp without time zone default now(),
  updated_at timestamp without time zone default now()
);

create table if not exists public.readings (
  id varchar primary key,
  kundli_id varchar not null references public.kundlis(id) on delete cascade,
  reading_type varchar not null,
  period_label varchar,
  generated_local_date varchar,
  version integer not null default 1,
  parent_reading_id varchar references public.readings(id) on delete set null,
  deviation_score double precision,
  deviation_summary jsonb,
  user_rating integer,
  user_feedback text,
  reviewed_at timestamp without time zone,
  content text not null,
  generated_at timestamp without time zone default now()
);

create table if not exists public.prediction_claims (
  id varchar primary key,
  kundli_id varchar not null references public.kundlis(id) on delete cascade,
  reading_id varchar not null references public.readings(id) on delete cascade,
  user_id varchar not null default 'local-dev-user',
  reading_type varchar not null,
  period_label varchar,
  generated_local_date varchar,
  target_start_date varchar,
  target_end_date varchar,
  category varchar not null default 'general',
  claim_text text not null,
  confidence double precision,
  source_excerpt text,
  status varchar not null default 'pending',
  user_feedback text,
  reviewed_at timestamp without time zone,
  created_at timestamp without time zone default now(),
  constraint prediction_claims_status_check
    check (status in ('pending', 'accurate', 'partly', 'missed', 'not_applicable'))
);

create index if not exists idx_kundlis_user_id
  on public.kundlis(user_id);

create index if not exists idx_readings_kundli_generated
  on public.readings(kundli_id, generated_local_date, generated_at desc);

create index if not exists idx_readings_period_version
  on public.readings(kundli_id, reading_type, period_label, version desc);

create index if not exists idx_prediction_claims_user_kundli
  on public.prediction_claims(user_id, kundli_id);

create index if not exists idx_prediction_claims_target
  on public.prediction_claims(kundli_id, target_start_date, target_end_date);

create index if not exists idx_prediction_claims_status
  on public.prediction_claims(user_id, status, category);

create table if not exists public.user_settings (
  user_id varchar primary key,
  chart_style varchar not null default 'south',
  ayanamsha varchar not null default 'lahiri',
  node_type varchar not null default 'mean',
  timezone_mode varchar not null default 'browser',
  panchanga_place jsonb,
  language varchar not null default 'en',
  regional_format varchar not null default 'en-IN',
  created_at timestamp without time zone default now(),
  updated_at timestamp without time zone default now(),
  constraint user_settings_chart_style_check
    check (chart_style in ('south', 'north')),
  constraint user_settings_ayanamsha_check
    check (ayanamsha in ('lahiri', 'raman', 'krishnamurti')),
  constraint user_settings_node_type_check
    check (node_type in ('mean', 'true')),
  constraint user_settings_timezone_mode_check
    check (timezone_mode in ('browser', 'panchanga_place'))
);

-- Optional direct-table protection if you later expose tables through Supabase client APIs.
-- The current app accesses these tables through FastAPI, so backend auth is the main guard.
alter table public.kundlis enable row level security;
alter table public.readings enable row level security;
alter table public.prediction_claims enable row level security;
alter table public.user_settings enable row level security;

do $$
begin
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'kundlis' and policyname = 'Users can read own kundlis') then
    create policy "Users can read own kundlis"
      on public.kundlis for select
      using (user_id = auth.uid()::text);
  end if;

  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'kundlis' and policyname = 'Users can manage own kundlis') then
    create policy "Users can manage own kundlis"
      on public.kundlis for all
      using (user_id = auth.uid()::text)
      with check (user_id = auth.uid()::text);
  end if;

  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'readings' and policyname = 'Users can read own readings') then
    create policy "Users can read own readings"
      on public.readings for select
      using (
        exists (
          select 1 from public.kundlis
          where kundlis.id = readings.kundli_id
            and kundlis.user_id = auth.uid()::text
        )
      );
  end if;

  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'readings' and policyname = 'Users can manage own readings') then
    create policy "Users can manage own readings"
      on public.readings for all
      using (
        exists (
          select 1 from public.kundlis
          where kundlis.id = readings.kundli_id
            and kundlis.user_id = auth.uid()::text
        )
      )
      with check (
        exists (
          select 1 from public.kundlis
          where kundlis.id = readings.kundli_id
            and kundlis.user_id = auth.uid()::text
        )
      );
  end if;

  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'prediction_claims' and policyname = 'Users can read own prediction claims') then
    create policy "Users can read own prediction claims"
      on public.prediction_claims for select
      using (user_id = auth.uid()::text);
  end if;

  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'prediction_claims' and policyname = 'Users can manage own prediction claims') then
    create policy "Users can manage own prediction claims"
      on public.prediction_claims for all
      using (user_id = auth.uid()::text)
      with check (user_id = auth.uid()::text);
  end if;

  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'user_settings' and policyname = 'Users can read own settings') then
    create policy "Users can read own settings"
      on public.user_settings for select
      using (user_id = auth.uid()::text);
  end if;

  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'user_settings' and policyname = 'Users can manage own settings') then
    create policy "Users can manage own settings"
      on public.user_settings for all
      using (user_id = auth.uid()::text)
      with check (user_id = auth.uid()::text);
  end if;
end $$;
