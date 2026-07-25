create table if not exists public.app_request_audit_log (
  id uuid primary key default gen_random_uuid(),
  actor_id text,
  actor_email text,
  method text not null,
  route text not null,
  status_code integer not null,
  resource_type text,
  resource_id text,
  request_id uuid not null default gen_random_uuid(),
  duration_ms integer,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists app_request_audit_created_idx
  on public.app_request_audit_log (created_at desc);
create index if not exists app_request_audit_actor_idx
  on public.app_request_audit_log (actor_id, created_at desc);
create index if not exists app_request_audit_route_idx
  on public.app_request_audit_log (route, created_at desc);

alter table public.app_request_audit_log enable row level security;
revoke all on public.app_request_audit_log from anon, authenticated;

drop trigger if exists app_request_audit_immutable
  on public.app_request_audit_log;
create trigger app_request_audit_immutable
before update or delete on public.app_request_audit_log
for each row execute function public.prevent_knowledge_audit_mutation();
