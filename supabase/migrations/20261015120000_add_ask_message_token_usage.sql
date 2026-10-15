-- Ask cost logging: tokens per assistant turn, including the repair pass.
--
-- The launch plan gates fixed Ask quotas on "cost per verified answer is
-- known", and nothing recorded it: ask_messages had `model` and `latency_ms`
-- columns that no route ever filled. The orchestrator now sums the token
-- usage of every model call behind an answer (first generation plus the
-- single repair attempt) and the routes persist it on the assistant turn;
-- `llm_calls` keeps the per-call breakdown (purpose, provider, model,
-- tokens) so a repair-heavy domain can be told apart from a verbose one.
--
-- Null on user turns and on refer-outs, which never reach a model.

alter table public.ask_messages
  add column if not exists input_tokens integer,
  add column if not exists output_tokens integer,
  add column if not exists llm_calls jsonb;
