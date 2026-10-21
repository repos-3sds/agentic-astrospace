-- "Report this answer" on Ask (Google Play's rule for apps with AI-generated
-- content: readers must be able to flag an answer from inside the app).
--
-- One row per report. The question and answer are copied in when the report
-- is made, so the team can still read what was reported after the reader
-- deletes the conversation; the links to the thread and message go null then.
-- Deleting the account deletes the reports (me_routes.delete_account).
--
-- Only the API writes it, as the backend role, and only /admin reads it. RLS
-- is on with no policy and both client roles lose every grant (the 2026-10-18
-- audit's S2/S21 rule for new tables).
create table if not exists public.answer_reports (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  thread_id uuid references public.ask_threads(id) on delete set null,
  message_id uuid references public.ask_messages(id) on delete set null,
  reason text not null check (reason in ('wrong', 'harmful', 'offensive', 'advice', 'other')),
  note text check (note is null or char_length(note) <= 1000),
  question text,
  answer text not null,
  experience_mode text,
  language text,
  status text not null default 'open' check (status in ('open', 'reviewed')),
  reviewed_at timestamptz,
  reviewed_by text,
  created_at timestamptz not null default now()
);

create index if not exists answer_reports_status_created
  on public.answer_reports(status, created_at desc);
create index if not exists answer_reports_user
  on public.answer_reports(user_id);

alter table public.answer_reports enable row level security;

do $$
declare
  r text;
begin
  foreach r in array array['authenticated', 'anon'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      execute format('revoke all on public.answer_reports from %I', r);
    end if;
  end loop;
end $$;
