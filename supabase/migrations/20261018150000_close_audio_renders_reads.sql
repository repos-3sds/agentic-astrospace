-- audio_renders was readable by everyone (2026-10-18 security audit S21).
--
-- "Users read audio renders" used `using (true)`, and the table was missing
-- from the anon revoke list, so any client could list every row's user_id,
-- kundli_id and storage_path. Nothing writes the table yet (put_audio_render
-- has no caller), so nothing was exposed; this closes it before something
-- does. The API reads it as the backend role, which RLS does not apply to.
drop policy if exists "Users read audio renders" on public.audio_renders;

do $$
declare
  r text;
begin
  foreach r in array array['authenticated', 'anon'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      execute format('revoke all on public.audio_renders from %I', r);
    end if;
  end loop;
end $$;
