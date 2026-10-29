-- Ask's crisis reply (agents/safety.py "crisis": a reader who says they are
-- thinking of ending their life gets care and helplines, never a reading) is
-- stored like the other refer-outs, with refer_out_kind 'crisis'. Widen the
-- check to allow it. Additive: every existing row still passes. Apply BEFORE
-- deploying the code that writes this kind, or the reply fails to save.

begin;

alter table ask_messages
  drop constraint if exists ask_messages_refer_out_kind_check;

alter table ask_messages
  add constraint ask_messages_refer_out_kind_check
  check (refer_out_kind in ('crisis', 'death', 'health', 'legal', 'money', 'out_of_scope', 'greeting'));

commit;
