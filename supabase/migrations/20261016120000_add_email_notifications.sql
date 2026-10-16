-- Email as a second delivery channel for the notification worker.
--
-- Two new opt-in categories (both off until the reader turns them on in
-- Settings > Notifications > Email), and one row per reader holding the
-- address we send to and whether the provider has told us to stop
-- (a hard bounce or a spam complaint). Account and sign-in emails are not
-- here: Supabase Auth sends those itself.

alter table public.notification_preferences
  drop constraint if exists notification_preferences_category_check;
alter table public.notification_preferences
  add constraint notification_preferences_category_check check (category in (
    'morning_brief',
    'window_alert',
    'festival_reminder',
    'remedy_reminder',
    'muhurta_reminder',
    'reading_ready',
    'accuracy_review',
    'match_report_ready',
    'system',
    'daily_email',        -- the day's brief, by email, in the morning
    'festival_email'      -- full moon, new moon and festival days, the evening before
  ));

create table if not exists public.email_recipients (
  user_id text primary key,
  email text not null,
  timezone text,
  -- Set from a provider webhook (hard bounce, spam complaint) or an
  -- unsubscribe-from-all. Nothing is sent to a suppressed address.
  suppressed_at timestamptz,
  suppressed_reason text,
  welcomed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_email_recipients_email
  on public.email_recipients(lower(email));

alter table public.email_recipients enable row level security;

-- Only the backend reads or writes addresses; clients go through /me/email.
do $$
declare
  r text;
begin
  foreach r in array array['postgres', 'service_role'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      execute format(
        'create policy %I on public.email_recipients for all to %I using (true) with check (true)',
        'Backend role full access ' || r, r
      );
      execute format('grant select, insert, update, delete on public.email_recipients to %I', r);
    end if;
  end loop;
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on public.email_recipients from anon;
  end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    revoke all on public.email_recipients from authenticated;
  end if;
end $$;
