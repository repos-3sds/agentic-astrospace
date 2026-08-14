alter table public.user_settings
  add column if not exists memory_enabled boolean not null default true,
  add column if not exists memory_mode text not null default 'ask';

alter table public.user_settings
  drop constraint if exists user_settings_memory_mode_check;
alter table public.user_settings
  add constraint user_settings_memory_mode_check
  check (memory_mode in ('ask', 'automatic'));
