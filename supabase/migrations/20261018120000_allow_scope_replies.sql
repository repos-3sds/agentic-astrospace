-- Ask's fixed replies for off-topic questions and greetings (agents/scope.py)
-- are stored like the safety refer-outs, with refer_out_kind 'out_of_scope'
-- or 'greeting'. Widen the check to allow them. Additive: every existing row
-- still passes. Apply BEFORE deploying the code that writes these kinds, or
-- the reply fails to save.

begin;

alter table ask_messages
  drop constraint if exists ask_messages_refer_out_kind_check;

alter table ask_messages
  add constraint ask_messages_refer_out_kind_check
  check (refer_out_kind in ('death', 'health', 'legal', 'money', 'out_of_scope', 'greeting'));

commit;
