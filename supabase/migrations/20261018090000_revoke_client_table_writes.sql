-- Signed-in clients may not write tables directly (2026-10-18 security audit S2).
--
-- The apps use supabase-js for auth only; every read and write goes through
-- the API, which connects as the backend role. But `authenticated` kept
-- Supabase's default grants, and 15+ tables carry "users manage own rows ...
-- for all" policies, so any signed-in user could call PostgREST with their
-- own JWT and insert rows the API would never accept: thousands of pending
-- notification_jobs ahead of everyone else's, a "system" email job with
-- their own subject, body and link, kundlis that skip validation, forged
-- ask_messages. Billing tables were safe only because they have no policy.
--
-- Reads stay as they are (own rows only, by the existing policies). Writes
-- are revoked from both client roles on every public table, and default
-- privileges stop new tables from getting them back.
do $$
declare
  t text;
  r text;
begin
  foreach r in array array['authenticated', 'anon'] loop
    if not exists (select 1 from pg_roles where rolname = r) then
      continue;
    end if;
    for t in select tablename from pg_tables where schemaname = 'public' loop
      execute format('revoke insert, update, delete, truncate on public.%I from %I', t, r);
    end loop;
    execute format(
      'alter default privileges in schema public revoke insert, update, delete, truncate on tables from %I', r);
  end loop;
end $$;
