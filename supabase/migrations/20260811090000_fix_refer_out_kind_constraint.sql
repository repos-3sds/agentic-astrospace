-- Fix ask_messages.refer_out_kind so safety refer-outs can actually persist.
--
-- P0, found by the Ask full-regression audit (docs/ask_full_regression_audit_2026-08-10.md,
-- ASK-001) and independently reproduced before this fix was written.
--
-- The original schema (20260725120000_create_mobile_app_schema.sql:169) constrained
-- this column to ('medical','legal','financial','longevity','emergency'), but the
-- application has always emitted ('death','health','legal','money') --
-- `astrospace.agents.safety.REFER_OUT_ANSWERS` -- and the mobile client's own
-- `ReferDomain` type agrees with the application, not the database.
--
-- Only 'legal' overlapped. So for the other three categories the safety gate fired
-- correctly, the assistant insert then violated ask_messages_refer_out_kind_check,
-- `_safe_stream` turned the CheckViolation into a `fatal_error` frame, and the
-- reader who asked "Will I die this year?" saw "Something went wrong while
-- generating this answer." instead of the mandatory referral to a professional.
-- The guardrail worked and the delivery of it failed, which is the worst shape
-- this failure can take.
--
-- Direction of the fix: the application and the client already agree, and they are
-- two layers against the database's one, so the database moves. Changing the
-- application vocabulary instead would mean touching a shared frontend union type
-- plus every safety pattern and test that keys off these names.
--
-- Existing rows are migrated rather than dropped. In practice no row can carry a
-- legacy value -- nothing ever emitted them and the constraint blocked everything
-- else -- but the UPDATEs run first so that if this database somehow does hold
-- one, the ALTER cannot fail halfway.
--
-- 'emergency' is retired without a canonical replacement: nothing in the
-- application emits it and no refer-out path produces it. Any such row (again,
-- not reachable in practice) is set to NULL, which the column already allows and
-- which reads correctly as "this message did not refer out". If a crisis/escalation
-- category is ever built, it should be added deliberately to REFER_OUT_ANSWERS and
-- to this constraint together, in that order.

begin;

update ask_messages set refer_out_kind = 'health' where refer_out_kind = 'medical';
update ask_messages set refer_out_kind = 'money'  where refer_out_kind = 'financial';
update ask_messages set refer_out_kind = 'death'  where refer_out_kind = 'longevity';
update ask_messages set refer_out_kind = null     where refer_out_kind = 'emergency';

alter table ask_messages
  drop constraint if exists ask_messages_refer_out_kind_check;

-- Canonical set. Must stay in lockstep with
-- `astrospace.agents.safety.REFER_OUT_ANSWERS`; tests/test_refer_out_persistence.py
-- fails if these two drift apart again, which is the check that was missing when
-- the original mismatch shipped.
alter table ask_messages
  add constraint ask_messages_refer_out_kind_check
  check (refer_out_kind in ('death', 'health', 'legal', 'money'));

commit;
