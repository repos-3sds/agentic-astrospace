"""Ask credits: reserve before an answer is generated, commit when it is
delivered, release when it is not.

Only a grounded answer that passed verification spends a credit. Refusals,
refer-outs, clarifications, "not ready" notices and failed generations are
terminal before or instead of an answer, and the routes release (or never
take) the reservation, so none of them costs the reader anything.

Order of spend: the monthly allowance first, then the oldest question pack.
The allowance is a usage_buckets row per calendar month (UTC); packs are
question_credits rows. Both are claimed with a conditional UPDATE, so two
answers racing for the last credit cannot both win.

Counting always happens. Blocking only happens when `quotas_enforced()` is
on, which stays off until store purchases are live.
"""
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db.models import QuestionCredit, UsageBucket
from .registry import quotas_enforced
from .resolver import EntitlementDecision, EntitlementDenied, resolve_entitlements

ASK_KEY = "ask.answers.period"


def month_bounds(now: datetime) -> tuple[str, datetime, datetime]:
    start = datetime(now.year, now.month, 1)
    end = datetime(now.year + (now.month == 12), now.month % 12 + 1, 1)
    return f"{now.year:04d}-{now.month:02d}", start, end


@dataclass
class AskReservation:
    """What one in-flight answer is holding. `kind` is 'allowance', 'pack' or
    'unmetered' (no limit applies, but the answer is still counted)."""
    kind: str
    row_id: str | None
    settled: bool = False


def _bucket(db: Session, account_id: str, now: datetime) -> UsageBucket:
    period_id, start, end = month_bounds(now)
    query = db.query(UsageBucket).filter(
        UsageBucket.billing_account_id == account_id,
        UsageBucket.scope_id == "account",
        UsageBucket.entitlement_key == ASK_KEY,
        UsageBucket.period_id == period_id,
    )
    bucket = query.one_or_none()
    if bucket:
        return bucket
    bucket = UsageBucket(
        billing_account_id=account_id, scope_id="account", entitlement_key=ASK_KEY,
        period_id=period_id, period_start=start, period_end=end,
    )
    db.add(bucket)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return query.one()
    db.refresh(bucket)
    return bucket


def reserve_ask_credit(db: Session, user_id: str, *, now: datetime | None = None) -> AskReservation:
    now = now or datetime.utcnow()
    snapshot = resolve_entitlements(db, user_id, now=now)
    limit = snapshot.entitlements.get(ASK_KEY)
    bucket = _bucket(db, snapshot.account_id, now)
    # Plain values, read before any commit: a commit expires `bucket`, and
    # touching it afterwards would open a new transaction just to reload it,
    # pinning a pooler connection through the model call that follows.
    bucket_id, period_end = bucket.id, bucket.period_end

    if limit is not None:
        claimed = db.execute(
            update(UsageBucket)
            .where(
                UsageBucket.id == bucket_id,
                UsageBucket.consumed + UsageBucket.reserved < int(limit),
            )
            .values(reserved=UsageBucket.reserved + 1, version=UsageBucket.version + 1)
        ).rowcount
        if claimed:
            db.commit()
            return AskReservation("allowance", bucket_id)

        packs = (
            db.query(QuestionCredit.id)
            .filter(
                QuestionCredit.billing_account_id == snapshot.account_id,
                QuestionCredit.remaining > 0,
                QuestionCredit.revoked_at.is_(None),
            )
            .order_by(QuestionCredit.created_at)
            .all()
        )
        for (pack_id,) in packs:
            claimed = db.execute(
                update(QuestionCredit)
                .where(QuestionCredit.id == pack_id, QuestionCredit.remaining > 0)
                .values(remaining=QuestionCredit.remaining - 1)
            ).rowcount
            if claimed:
                db.commit()
                return AskReservation("pack", pack_id)
        db.rollback()

        if quotas_enforced():
            raise EntitlementDenied(EntitlementDecision(
                False, ASK_KEY, limit, "limit_reached", snapshot.access_tier,
                remaining=0, resets_at=period_end.isoformat(),
            ))

    # No limit, or a limit that is counted but not yet enforced: the answer
    # goes ahead and still lands in this month's count.
    db.execute(
        update(UsageBucket)
        .where(UsageBucket.id == bucket_id)
        .values(reserved=UsageBucket.reserved + 1, version=UsageBucket.version + 1)
    )
    db.commit()
    return AskReservation("unmetered", bucket_id)


def commit_ask_credit(db: Session, reservation: AskReservation | None) -> None:
    """The answer was delivered: the held credit becomes spent."""
    if reservation is None or reservation.settled:
        return
    reservation.settled = True
    if reservation.kind in {"allowance", "unmetered"}:
        db.execute(
            update(UsageBucket)
            .where(UsageBucket.id == reservation.row_id, UsageBucket.reserved > 0)
            .values(
                reserved=UsageBucket.reserved - 1,
                consumed=UsageBucket.consumed + 1,
                version=UsageBucket.version + 1,
            )
        )
        db.commit()
    # A pack credit was already taken off `remaining` when reserved.


def release_ask_credit(db: Session, reservation: AskReservation | None) -> None:
    """The answer was not delivered: give the credit back."""
    if reservation is None or reservation.settled:
        return
    reservation.settled = True
    try:
        if reservation.kind in {"allowance", "unmetered"}:
            db.execute(
                update(UsageBucket)
                .where(UsageBucket.id == reservation.row_id, UsageBucket.reserved > 0)
                .values(reserved=UsageBucket.reserved - 1, version=UsageBucket.version + 1)
            )
        else:
            db.execute(
                update(QuestionCredit)
                .where(QuestionCredit.id == reservation.row_id)
                .values(remaining=QuestionCredit.remaining + 1)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def question_credits_remaining(db: Session, account_id: str) -> int:
    rows = db.query(QuestionCredit.remaining).filter(
        QuestionCredit.billing_account_id == account_id,
        QuestionCredit.revoked_at.is_(None),
    ).all()
    return sum(remaining for (remaining,) in rows)


COMPAT_KEY = "compatibility.checks.period"


def record_compatibility_check(db: Session, user_id: str, person_id: str,
                               *, now: datetime | None = None) -> None:
    """Count one person checked for compatibility this month, or refuse (402).

    Free has one person a month. The count used to live only on the phone
    (plan-gate.service.ts, sweep 2026-10-29 G-6). It is one usage_buckets row
    per person, with the person as `scope_id`, so re-opening someone already
    checked costs nothing and two requests for the same person can't count
    twice. Blocks only when quotas are enforced, like every other limit.
    """
    from .resolver import require_turn

    now = now or datetime.utcnow()
    snapshot = resolve_entitlements(db, user_id, now=now)
    period_id, start, end = month_bounds(now)
    checked = {
        row.scope_id for row in db.query(UsageBucket.scope_id).filter(
            UsageBucket.billing_account_id == snapshot.account_id,
            UsageBucket.entitlement_key == COMPAT_KEY,
            UsageBucket.period_id == period_id,
        )
    }
    if person_id in checked:
        return
    require_turn(db, user_id, COMPAT_KEY, len(checked), now=now)
    db.add(UsageBucket(
        billing_account_id=snapshot.account_id, scope_id=person_id, entitlement_key=COMPAT_KEY,
        period_id=period_id, period_start=start, period_end=end, consumed=1,
    ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # the same person, counted by a request racing this one
