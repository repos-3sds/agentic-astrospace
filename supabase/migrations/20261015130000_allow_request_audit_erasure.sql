-- Account deletion: erase the actor from the request audit log.
--
-- app_request_audit_log is append-only (trigger app_request_audit_immutable),
-- and it stored every mutating request's actor_email forever, including after
-- the account was deleted. DELETE /api/v1/me now clears the email and replaces
-- actor_id with a pseudonym on that person's rows.
--
-- This replaces the table's trigger function with one that still refuses
-- every DELETE and every UPDATE except exactly that erasure: actor_email set
-- to null, actor_id set to 'erased:' || md5(old actor_id), every other column
-- unchanged. The app computes the same pseudonym
-- (astrospace/admin/audit_middleware.py pseudonymous_actor_id). The shared
-- knowledge_audit_log keeps the original, stricter function.
--
-- Apply before deploying the code that calls it; until then the erasure is
-- refused by the old trigger and logged as a failure, and deletion proceeds.

create or replace function public.guard_app_request_audit_mutation()
returns trigger
language plpgsql
as $$
begin
  if tg_op = 'UPDATE'
     and old.actor_id is not null
     and new.actor_email is null
     and new.actor_id = 'erased:' || md5(old.actor_id)
     and new.id = old.id
     and new.method = old.method
     and new.route = old.route
     and new.status_code = old.status_code
     and new.resource_type is not distinct from old.resource_type
     and new.resource_id is not distinct from old.resource_id
     and new.request_id = old.request_id
     and new.duration_ms is not distinct from old.duration_ms
     and new.metadata = old.metadata
     and new.created_at = old.created_at
  then
    return new;
  end if;
  raise exception 'app_request_audit_log is append-only (only actor erasure is allowed)';
end;
$$;

drop trigger if exists app_request_audit_immutable
  on public.app_request_audit_log;
create trigger app_request_audit_immutable
before update or delete on public.app_request_audit_log
for each row execute function public.guard_app_request_audit_mutation();
