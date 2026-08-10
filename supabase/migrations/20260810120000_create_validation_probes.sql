-- Validation probes — the consultation validation loop's commit-before-ask store.
--
-- A real astrologer validates before predicting. Doing that naively in software
-- produces a cold-reading machine: ask "have you had money trouble?", hear yes,
-- reply "your chart shows that". Nothing was tested and the reader was handed
-- their own disclosure back as insight.
--
-- What makes it honest is ordering. The agent commits to a falsifiable claim,
-- with a confidence, BEFORE the question is put — so claim_text, claim_candidate,
-- confidence and committed_at are all NOT NULL at insert, while answer_key and
-- answered_at can only be filled in afterwards. A row is therefore self-evidently
-- a prediction that preceded its own test, and a hit rate computed over these
-- rows means something.
--
-- Not folded into prediction_claims: that table's reading_id is a NOT NULL FK
-- into readings, and an Ask-side probe has no readings row to point at (Ask
-- persists ask_messages). A probe also carries a question and its options, which
-- a forward prediction never does.

create table if not exists public.validation_probes (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  kundli_id text not null references public.kundlis(id) on delete cascade,
  thread_id uuid references public.ask_threads(id) on delete set null,
  domain text not null,

  -- the slot the ENGINE picked; the model only writes question/options
  slot_id text not null,
  slot_kind text not null,
  anchor_start text,
  anchor_end text,
  anchor_label text,

  -- the commitment, written before the question is asked
  claim_text text not null,
  claim_candidate text not null,
  confidence double precision not null,
  committed_at timestamptz not null default now(),

  -- the question put to the reader
  question text not null,
  options jsonb not null default '[]'::jsonb,

  -- what came back, and how the commitment scored
  answer_key text,
  answer_text text,
  answered_at timestamptz,
  status text not null default 'committed'
    check (status in ('committed', 'confirmed', 'missed', 'partial', 'skipped')),
  created_at timestamptz not null default now(),

  -- an answer cannot exist without a scored status, and vice versa
  constraint validation_probes_answer_consistent check (
    (answered_at is null and status = 'committed')
    or (answered_at is not null and status <> 'committed')
  )
);

-- "Asked once" is a product requirement (question fatigue is the main way this
-- loop stops being worth answering), enforced here rather than in app code.
create unique index if not exists validation_probes_user_kundli_slot_key
  on public.validation_probes(user_id, kundli_id, slot_id);

create index if not exists idx_validation_probes_user_kundli_domain
  on public.validation_probes(user_id, kundli_id, domain, committed_at desc);

alter table public.validation_probes enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'validation_probes'
      and policyname = 'Users manage own validation probes'
  ) then
    create policy "Users manage own validation probes" on public.validation_probes for all
      using (user_id = auth.uid()::text)
      with check (user_id = auth.uid()::text);
  end if;
end $$;

-- Mirrors 20260725130000's two roles-and-grants passes for every app table.
-- Without the backend policy the API (which reaches Postgres as service_role)
-- gets zero rows from its own table; without the anon revoke this would be the
-- one personal table the browser role can still reach directly, since the SPA
-- uses supabase-js for auth only and all data goes through FastAPI.
do $$
declare
  r text;
  backend_roles text[] := array['postgres', 'service_role'];
begin
  foreach r in array backend_roles loop
    if not exists (select 1 from pg_roles where rolname = r) then
      continue;
    end if;
    if not exists (
      select 1 from pg_policies
      where schemaname = 'public' and tablename = 'validation_probes'
        and policyname = 'Backend role full access ' || r
    ) then
      execute format(
        'create policy %I on public.validation_probes for all to %I using (true) with check (true)',
        'Backend role full access ' || r, r);
    end if;
  end loop;
end $$;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke select, insert, update, delete on public.validation_probes from anon;
  end if;
end $$;
