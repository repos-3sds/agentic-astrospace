-- Applied to the live database on 2026-10-17 through the Supabase connector
-- (from the security advisors) without a file in the repo; added here on
-- 2026-10-18 so the repo matches the recorded migration history.
--
-- rls_auto_enable() is an admin helper: no client role may call it. The
-- trigger functions get a fixed search_path so a schema on the caller's path
-- can't shadow the tables they touch.
REVOKE EXECUTE ON FUNCTION public.rls_auto_enable() FROM PUBLIC, anon, authenticated;
ALTER FUNCTION public.set_updated_at() SET search_path = public, pg_temp;
ALTER FUNCTION public.prevent_knowledge_audit_mutation() SET search_path = public, pg_temp;
ALTER FUNCTION public.prevent_knowledge_section_text_update() SET search_path = public, pg_temp;
ALTER FUNCTION public.prevent_knowledge_chunk_text_update() SET search_path = public, pg_temp;
