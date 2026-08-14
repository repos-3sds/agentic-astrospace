"""CRUD for the mobile app schema (20260725120000_create_mobile_app_schema.sql).

Kept separate from crud.py so that file stays focused on the original four
tables; both follow the same conventions — Session first, commit + refresh on
write, optional user_id filtering for ownership.

Note on authorisation: these helpers filter by user_id where the caller passes
one. Ownership is enforced by the API layer (astrospace/api/auth.py resolves the
Supabase bearer token to a user id) and, at the database level, by RLS policies.
"""

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (
    AskMessage,
    AskThread,
    AudioRender,
    CompatibilityCheck,
    DailyGuidanceCache,
    Festival,
    FestivalOccurrence,
    GlossaryTerm,
    LiveActivity,
    MuhurtaRequest,
    NotificationDelivery,
    NotificationJob,
    NotificationPreference,
    PushToken,
    Remedy,
    RemedyCompletion,
    SavedMuhurta,
    ShareAsset,
    UserAlert,
    UserDevice,
    UserObservance,
    UserProfile,
    UserRemedy,
    ValidationProbe,
    WidgetInstall,
)
from ..context.validation import score_answer

# Defaults mirror the Settings > Notifications screen. Remedy reminders are the
# one category that starts off — it only makes sense once a remedy is active.
DEFAULT_NOTIFICATION_PREFS: dict[str, dict] = {
    "morning_brief": {"enabled": True, "preferred_time": None},
    "window_alert": {"enabled": True, "lead_time_minutes": 45},
    "festival_reminder": {"enabled": True, "lead_time_days": 3},
    "remedy_reminder": {"enabled": False},
    "muhurta_reminder": {"enabled": True, "lead_time_minutes": 60},
    "reading_ready": {"enabled": True},
    "accuracy_review": {"enabled": True},
    "match_report_ready": {"enabled": True},
    "system": {"enabled": True},
}


# ── Profile & devices ─────────────────────────────────────────────────────────

def get_or_create_user_profile(db: Session, user_id: str, **defaults) -> UserProfile:
    profile = db.get(UserProfile, user_id)
    if profile:
        return profile
    profile = UserProfile(user_id=user_id, **defaults)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_user_profile(db: Session, user_id: str, data: dict) -> UserProfile | None:
    profile = db.get(UserProfile, user_id)
    if not profile:
        return None
    for key, val in data.items():
        setattr(profile, key, val)
    db.commit()
    db.refresh(profile)
    return profile


def upsert_device(db: Session, user_id: str, device_id: str, data: dict) -> UserDevice:
    """Register or refresh a device. Called on app launch."""
    device = (
        db.query(UserDevice)
        .filter(UserDevice.user_id == user_id, UserDevice.device_id == device_id)
        .first()
    )
    if device:
        for key, val in data.items():
            setattr(device, key, val)
        device.last_seen_at = datetime.utcnow()
    else:
        device = UserDevice(user_id=user_id, device_id=device_id, **data)
        db.add(device)
    db.commit()
    db.refresh(device)
    return device


# ── Ask ───────────────────────────────────────────────────────────────────────

def create_ask_thread(db: Session, user_id: str, kundli_id: str, title: str | None = None) -> AskThread:
    thread = AskThread(user_id=user_id, kundli_id=kundli_id, title=title)
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


def list_ask_threads(db: Session, user_id: str, kundli_id: str | None = None,
                     limit: int = 50, archived: bool = False) -> list[AskThread]:
    archived_filter = AskThread.archived_at.is_not(None) if archived else AskThread.archived_at.is_(None)
    q = db.query(AskThread).filter(AskThread.user_id == user_id, archived_filter)
    if kundli_id is not None:
        q = q.filter(AskThread.kundli_id == kundli_id)
    return q.order_by(AskThread.last_message_at.desc().nullslast()).limit(limit).all()


def get_ask_thread(db: Session, thread_id: str, user_id: str | None = None) -> AskThread | None:
    q = db.query(AskThread).filter(AskThread.id == thread_id)
    if user_id is not None:
        q = q.filter(AskThread.user_id == user_id)
    return q.first()


def add_ask_message(db: Session, thread_id: str, role: str, content: str, **fields) -> AskMessage:
    """Append a message and keep the thread's denormalised counters in step."""
    message = AskMessage(thread_id=thread_id, role=role, content=content, **fields)
    db.add(message)

    thread = db.get(AskThread, thread_id)
    if thread:
        thread.last_message_at = datetime.utcnow()
        thread.message_count = (thread.message_count or 0) + 1
        # First user message doubles as the thread title.
        if not thread.title and role == "user":
            thread.title = content[:80]

    db.commit()
    db.refresh(message)
    return message


def get_thread_messages(db: Session, thread_id: str, limit: int = 200) -> list[AskMessage]:
    return (
        db.query(AskMessage)
        .filter(AskMessage.thread_id == thread_id)
        .order_by(AskMessage.created_at)
        .limit(limit)
        .all()
    )


def archive_ask_thread(db: Session, thread_id: str, user_id: str) -> bool:
    thread = get_ask_thread(db, thread_id, user_id)
    if not thread:
        return False
    thread.archived_at = datetime.utcnow()
    db.commit()
    return True


def restore_ask_thread(db: Session, thread_id: str, user_id: str) -> bool:
    thread = get_ask_thread(db, thread_id, user_id)
    if not thread:
        return False
    thread.archived_at = None
    db.commit()
    return True


def delete_ask_thread(db: Session, thread_id: str, user_id: str) -> bool:
    thread = get_ask_thread(db, thread_id, user_id)
    if not thread:
        return False
    db.delete(thread)
    db.commit()
    return True


# ── Validation probes ─────────────────────────────────────────────────────────
#
# The ordering guarantee lives in these three functions, not in a comment: the
# only write path that creates a row supplies the claim, and the only write path
# that records an answer cannot touch it. See ValidationProbe's docstring.

def commit_validation_probe(db: Session, user_id: str, kundli_id: str, domain: str,
                            slot: dict, claim_text: str, claim_candidate: str,
                            confidence: float, question: str, options: list,
                            thread_id: str | None = None) -> ValidationProbe:
    """Write the commitment. Called BEFORE the question reaches the reader —
    that is the entire contract, and `committed_at` is stamped here so a row
    can be checked against `answered_at` after the fact."""
    anchor = slot.get("anchor") or {}
    probe = ValidationProbe(
        user_id=user_id, kundli_id=kundli_id, thread_id=thread_id, domain=domain,
        slot_id=slot["slot_id"], slot_kind=slot["kind"],
        anchor_start=anchor.get("start"), anchor_end=anchor.get("end"),
        anchor_label=anchor.get("label"),
        claim_text=claim_text, claim_candidate=claim_candidate,
        confidence=confidence, committed_at=datetime.utcnow(),
        question=question, options=options, status="committed",
    )
    db.add(probe)
    try:
        db.commit()
    except Exception:
        # The caller's fail-open is only real if the session survives the
        # failure. Without this rollback a rejected insert — the unique
        # "asked once" index firing on two concurrent turns is enough — leaves
        # the session in a failed transaction, and the very next query is the
        # one assembling the READING. The reader loses their answer to a
        # bonus feature's collision, which is the exact opposite of the
        # contract `AskOrchestrator.check_validation` documents. Re-raised so
        # the caller still knows the probe did not happen.
        db.rollback()
        raise
    db.refresh(probe)
    return probe


def record_validation_answer(db: Session, probe_id: str, user_id: str,
                             answer_key: str, answer_text: str | None = None
                             ) -> ValidationProbe | None:
    """Score a committed claim against what the reader said.

    Touches answer columns and `status` only. The claim, its confidence and its
    commit timestamp are deliberately not parameters of this function — there
    is no code path that can revise a prediction after seeing its answer, which
    is what makes the stored hit rate worth computing.

    Answering twice is refused rather than overwritten: a probe is one test.
    """
    probe = (
        db.query(ValidationProbe)
        .filter(ValidationProbe.id == probe_id, ValidationProbe.user_id == user_id)
        .first()
    )
    if probe is None or probe.status != "committed":
        return None
    # An answer the probe never offered is not an answer. Without this the
    # endpoint accepts any string, and `answer_key` reaches `score_answer()`
    # (where an unknown key silently scores as a miss, corrupting the hit rate
    # this whole loop exists to produce) and `life_context`, which the reading
    # prompt is told outranks the chart.
    offered = {option.get("key") for option in (probe.options or [])}
    if offered and answer_key not in offered:
        return None
    probe.answer_key = answer_key
    probe.answer_text = answer_text
    probe.answered_at = datetime.utcnow()
    probe.status = score_answer(probe.claim_candidate, answer_key)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(probe)
    return probe


def list_validation_probes(db: Session, user_id: str, kundli_id: str,
                           domain: str | None = None,
                           answered_only: bool = False) -> list[ValidationProbe]:
    query = (
        db.query(ValidationProbe)
        .filter(ValidationProbe.user_id == user_id,
                ValidationProbe.kundli_id == kundli_id)
    )
    if domain:
        query = query.filter(ValidationProbe.domain == domain)
    if answered_only:
        query = query.filter(ValidationProbe.answered_at.isnot(None))
    return query.order_by(ValidationProbe.committed_at).all()


# ── Remedies ──────────────────────────────────────────────────────────────────

def list_remedies(db: Session, remedy_type: str | None = None, language: str = "en") -> list[Remedy]:
    q = db.query(Remedy).filter(Remedy.is_active.is_(True), Remedy.language == language)
    if remedy_type is not None:
        q = q.filter(Remedy.remedy_type == remedy_type)
    return q.order_by(Remedy.title).all()


def start_user_remedy(db: Session, user_id: str, kundli_id: str, remedy_id: str, **fields) -> UserRemedy:
    user_remedy = UserRemedy(user_id=user_id, kundli_id=kundli_id, remedy_id=remedy_id, **fields)
    db.add(user_remedy)
    db.commit()
    db.refresh(user_remedy)
    return user_remedy


def list_user_remedies(db: Session, user_id: str, kundli_id: str | None = None,
                       status: str | None = "active") -> list[UserRemedy]:
    q = db.query(UserRemedy).filter(UserRemedy.user_id == user_id)
    if kundli_id is not None:
        q = q.filter(UserRemedy.kundli_id == kundli_id)
    if status is not None:
        q = q.filter(UserRemedy.status == status)
    return q.order_by(UserRemedy.started_at.desc()).all()


def update_user_remedy(db: Session, user_remedy_id: str, user_id: str, data: dict) -> UserRemedy | None:
    user_remedy = (
        db.query(UserRemedy)
        .filter(UserRemedy.id == user_remedy_id, UserRemedy.user_id == user_id)
        .first()
    )
    if not user_remedy:
        return None
    for key, val in data.items():
        setattr(user_remedy, key, val)
    if data.get("status") == "completed" and not user_remedy.completed_at:
        user_remedy.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(user_remedy)
    return user_remedy


def log_remedy_completion(db: Session, user_remedy_id: str, on: date | None = None,
                          count: int = 1) -> RemedyCompletion:
    """Record (or increment) today's completion. One row per day — the unique
    constraint on (user_remedy_id, occurred_on) makes this idempotent per day."""
    on = on or date.today()
    completion = (
        db.query(RemedyCompletion)
        .filter(
            RemedyCompletion.user_remedy_id == user_remedy_id,
            RemedyCompletion.occurred_on == on,
        )
        .first()
    )
    if completion:
        completion.count = (completion.count or 0) + count
    else:
        completion = RemedyCompletion(user_remedy_id=user_remedy_id, occurred_on=on, count=count)
        db.add(completion)
    db.commit()
    db.refresh(completion)
    return completion


def get_remedy_streak(db: Session, user_remedy_id: str, today: date | None = None) -> int:
    """Consecutive days completed, counting back from today.

    A streak stays alive if the practice was done today *or* yesterday — so it
    does not break simply because the user has not opened the app yet today.
    """
    today = today or date.today()
    days = [
        row[0]
        for row in db.query(RemedyCompletion.occurred_on)
        .filter(RemedyCompletion.user_remedy_id == user_remedy_id)
        .order_by(RemedyCompletion.occurred_on.desc())
        .all()
    ]
    if not days:
        return 0

    done = set(days)
    if today in done:
        cursor = today
    elif (today - timedelta(days=1)) in done:
        cursor = today - timedelta(days=1)
    else:
        return 0

    streak = 0
    while cursor in done:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


# ── Muhurta ───────────────────────────────────────────────────────────────────

def create_muhurta_request(db: Session, user_id: str, kundli_id: str, goal_slug: str,
                           date_from: date, date_to: date, **fields) -> MuhurtaRequest:
    request = MuhurtaRequest(
        user_id=user_id, kundli_id=kundli_id, goal_slug=goal_slug,
        date_from=date_from, date_to=date_to, **fields,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def complete_muhurta_request(db: Session, request_id: str, results: list) -> MuhurtaRequest | None:
    request = db.get(MuhurtaRequest, request_id)
    if not request:
        return None
    request.results = results
    request.status = "ready" if results else "empty"
    request.computed_at = datetime.utcnow()
    db.commit()
    db.refresh(request)
    return request


def save_muhurta(db: Session, user_id: str, kundli_id: str, starts_at: datetime,
                 ends_at: datetime, **fields) -> SavedMuhurta:
    saved = SavedMuhurta(
        user_id=user_id, kundli_id=kundli_id, starts_at=starts_at, ends_at=ends_at, **fields
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return saved


def list_saved_muhurtas(db: Session, user_id: str, upcoming_only: bool = True) -> list[SavedMuhurta]:
    q = db.query(SavedMuhurta).filter(SavedMuhurta.user_id == user_id)
    if upcoming_only:
        q = q.filter(SavedMuhurta.ends_at >= datetime.utcnow())
    return q.order_by(SavedMuhurta.starts_at).all()


# ── Festivals & observances ───────────────────────────────────────────────────

def list_upcoming_festivals(db: Session, place_key: str = "default", days: int = 60,
                            today: date | None = None) -> list[tuple[FestivalOccurrence, Festival]]:
    today = today or date.today()
    return (
        db.query(FestivalOccurrence, Festival)
        .join(Festival, Festival.id == FestivalOccurrence.festival_id)
        .filter(
            FestivalOccurrence.place_key == place_key,
            FestivalOccurrence.occurs_on >= today,
            FestivalOccurrence.occurs_on <= today + timedelta(days=days),
            Festival.is_active.is_(True),
        )
        .order_by(FestivalOccurrence.occurs_on)
        .all()
    )


def set_observance(db: Session, user_id: str, festival_id: str, occurs_on: date,
                   **fields) -> UserObservance:
    observance = (
        db.query(UserObservance)
        .filter(
            UserObservance.user_id == user_id,
            UserObservance.festival_id == festival_id,
            UserObservance.occurs_on == occurs_on,
        )
        .first()
    )
    if observance:
        for key, val in fields.items():
            setattr(observance, key, val)
    else:
        observance = UserObservance(
            user_id=user_id, festival_id=festival_id, occurs_on=occurs_on, **fields
        )
        db.add(observance)
    db.commit()
    db.refresh(observance)
    return observance


# ── Compatibility ─────────────────────────────────────────────────────────────

def save_compatibility_check(db: Session, user_id: str, kundli_id: str,
                             partner_kundli_id: str, **fields) -> CompatibilityCheck:
    check = CompatibilityCheck(
        user_id=user_id, kundli_id=kundli_id, partner_kundli_id=partner_kundli_id, **fields
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return check


def list_compatibility_checks(db: Session, user_id: str, limit: int = 20) -> list[CompatibilityCheck]:
    return (
        db.query(CompatibilityCheck)
        .filter(CompatibilityCheck.user_id == user_id)
        .order_by(CompatibilityCheck.created_at.desc())
        .limit(limit)
        .all()
    )


# ── Notifications: tokens & preferences ───────────────────────────────────────

def upsert_push_token(db: Session, user_id: str, provider: str, token: str, **fields) -> PushToken:
    """Tokens are unique per (provider, token) and can migrate between users
    when a device changes hands, so reassign rather than duplicate."""
    row = (
        db.query(PushToken)
        .filter(PushToken.provider == provider, PushToken.token == token)
        .first()
    )
    if row:
        row.user_id = user_id
        row.revoked_at = None
        row.last_seen_at = datetime.utcnow()
        for key, val in fields.items():
            setattr(row, key, val)
    else:
        row = PushToken(user_id=user_id, provider=provider, token=token, **fields)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def revoke_push_token(db: Session, provider: str, token: str) -> bool:
    row = (
        db.query(PushToken)
        .filter(PushToken.provider == provider, PushToken.token == token)
        .first()
    )
    if not row:
        return False
    row.revoked_at = datetime.utcnow()
    db.commit()
    return True


def list_active_push_tokens(db: Session, user_id: str) -> list[PushToken]:
    return (
        db.query(PushToken)
        .filter(PushToken.user_id == user_id, PushToken.revoked_at.is_(None))
        .all()
    )


def get_notification_preferences(db: Session, user_id: str) -> dict[str, dict]:
    """Stored rows merged over the defaults, so every category always resolves."""
    prefs = {cat: dict(vals) for cat, vals in DEFAULT_NOTIFICATION_PREFS.items()}
    rows = db.query(NotificationPreference).filter(NotificationPreference.user_id == user_id).all()
    for row in rows:
        prefs.setdefault(row.category, {})
        prefs[row.category].update({
            "enabled": row.enabled,
            "channels": row.channels,
            "lead_time_minutes": row.lead_time_minutes,
            "lead_time_days": row.lead_time_days,
            "preferred_time": row.preferred_time,
            "quiet_hours_start": row.quiet_hours_start,
            "quiet_hours_end": row.quiet_hours_end,
            "timezone": row.timezone,
        })
    return prefs


def set_notification_preference(db: Session, user_id: str, category: str,
                                **fields) -> NotificationPreference:
    row = (
        db.query(NotificationPreference)
        .filter(
            NotificationPreference.user_id == user_id,
            NotificationPreference.category == category,
        )
        .first()
    )
    if row:
        for key, val in fields.items():
            setattr(row, key, val)
    else:
        row = NotificationPreference(user_id=user_id, category=category, **fields)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ── Notifications: scheduling & delivery ──────────────────────────────────────

def schedule_notification(db: Session, user_id: str, category: str, scheduled_for: datetime,
                          title: str, dedupe_key: str | None = None, **fields) -> NotificationJob:
    """Idempotent when a dedupe_key is supplied — re-running a scheduler for the
    same day returns the existing job instead of queuing a duplicate."""
    if dedupe_key:
        existing = (
            db.query(NotificationJob)
            .filter(NotificationJob.dedupe_key == dedupe_key)
            .first()
        )
        if existing:
            return existing

    job = NotificationJob(
        user_id=user_id, category=category, scheduled_for=scheduled_for,
        title=title, dedupe_key=dedupe_key, **fields,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def claim_due_notifications(db: Session, limit: int = 100,
                            now: datetime | None = None) -> list[NotificationJob]:
    """Atomically move due jobs to 'processing' so concurrent workers cannot
    both send the same push. Uses SKIP LOCKED on Postgres; SQLite (local dev)
    is single-writer so the plain query is safe there."""
    now = now or datetime.utcnow()
    q = (
        db.query(NotificationJob)
        .filter(NotificationJob.status == "pending", NotificationJob.scheduled_for <= now)
        .order_by(NotificationJob.scheduled_for)
        .limit(limit)
    )
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        q = q.with_for_update(skip_locked=True)

    jobs = q.all()
    for job in jobs:
        job.status = "processing"
        job.attempts = (job.attempts or 0) + 1
    db.commit()
    return jobs


def mark_notification_sent(db: Session, job_id: str) -> NotificationJob | None:
    job = db.get(NotificationJob, job_id)
    if not job:
        return None
    job.status = "sent"
    job.sent_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return job


def mark_notification_failed(db: Session, job_id: str, error: str,
                             retry: bool = True, max_attempts: int = 5) -> NotificationJob | None:
    job = db.get(NotificationJob, job_id)
    if not job:
        return None
    job.last_error = error[:2000]
    job.status = "pending" if (retry and (job.attempts or 0) < max_attempts) else "failed"
    db.commit()
    db.refresh(job)
    return job


def cancel_notification(db: Session, job_id: str, reason: str | None = None) -> bool:
    job = db.get(NotificationJob, job_id)
    if not job or job.status in ("sent", "cancelled"):
        return False
    job.status = "cancelled"
    job.skip_reason = reason
    db.commit()
    return True


def record_delivery(db: Session, job_id: str, status: str, **fields) -> NotificationDelivery:
    delivery = NotificationDelivery(job_id=job_id, status=status, **fields)
    db.add(delivery)
    db.commit()
    db.refresh(delivery)
    return delivery


# ── In-app alerts ─────────────────────────────────────────────────────────────

def create_alert(db: Session, user_id: str, category: str, title: str, **fields) -> UserAlert:
    alert = UserAlert(user_id=user_id, category=category, title=title, **fields)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def list_alerts(db: Session, user_id: str, unread_only: bool = False,
                limit: int = 50) -> list[UserAlert]:
    now = datetime.utcnow()
    q = db.query(UserAlert).filter(
        UserAlert.user_id == user_id,
        UserAlert.dismissed_at.is_(None),
    )
    if unread_only:
        q = q.filter(UserAlert.read_at.is_(None))
    q = q.filter((UserAlert.expires_at.is_(None)) | (UserAlert.expires_at > now))
    return q.order_by(UserAlert.created_at.desc()).limit(limit).all()


def count_unread_alerts(db: Session, user_id: str) -> int:
    now = datetime.utcnow()
    return (
        db.query(func.count(UserAlert.id))
        .filter(
            UserAlert.user_id == user_id,
            UserAlert.read_at.is_(None),
            UserAlert.dismissed_at.is_(None),
            (UserAlert.expires_at.is_(None)) | (UserAlert.expires_at > now),
        )
        .scalar()
    ) or 0


def mark_alert_read(db: Session, alert_id: str, user_id: str) -> bool:
    alert = db.query(UserAlert).filter(UserAlert.id == alert_id, UserAlert.user_id == user_id).first()
    if not alert:
        return False
    alert.read_at = alert.read_at or datetime.utcnow()
    db.commit()
    return True


def dismiss_alert(db: Session, alert_id: str, user_id: str) -> bool:
    alert = db.query(UserAlert).filter(UserAlert.id == alert_id, UserAlert.user_id == user_id).first()
    if not alert:
        return False
    alert.dismissed_at = datetime.utcnow()
    db.commit()
    return True


# ── Native surfaces ───────────────────────────────────────────────────────────

def upsert_widget_install(db: Session, user_id: str, kind: str, **fields) -> WidgetInstall:
    widget = WidgetInstall(user_id=user_id, kind=kind, **fields)
    db.add(widget)
    db.commit()
    db.refresh(widget)
    return widget


def start_live_activity(db: Session, user_id: str, kind: str, starts_at: datetime,
                        ends_at: datetime, **fields) -> LiveActivity:
    activity = LiveActivity(
        user_id=user_id, kind=kind, starts_at=starts_at, ends_at=ends_at, **fields
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


def end_live_activity(db: Session, activity_id: str, status: str = "ended") -> bool:
    activity = db.get(LiveActivity, activity_id)
    if not activity:
        return False
    activity.status = status
    db.commit()
    return True


def list_active_live_activities(db: Session, user_id: str) -> list[LiveActivity]:
    return (
        db.query(LiveActivity)
        .filter(LiveActivity.user_id == user_id, LiveActivity.status == "active")
        .order_by(LiveActivity.ends_at)
        .all()
    )


# ── Caches ────────────────────────────────────────────────────────────────────

def get_cached_daily_guidance(db: Session, kundli_id: str, local_date: date,
                              conventions_hash: str, language: str = "en") -> DailyGuidanceCache | None:
    row = (
        db.query(DailyGuidanceCache)
        .filter(
            DailyGuidanceCache.kundli_id == kundli_id,
            DailyGuidanceCache.local_date == local_date,
            DailyGuidanceCache.conventions_hash == conventions_hash,
            DailyGuidanceCache.language == language,
        )
        .first()
    )
    if row and row.expires_at and row.expires_at < datetime.utcnow():
        return None
    return row


def put_cached_daily_guidance(db: Session, kundli_id: str, local_date: date, conventions_hash: str,
                              payload: dict, language: str = "en", **fields) -> DailyGuidanceCache:
    row = (
        db.query(DailyGuidanceCache)
        .filter(
            DailyGuidanceCache.kundli_id == kundli_id,
            DailyGuidanceCache.local_date == local_date,
            DailyGuidanceCache.conventions_hash == conventions_hash,
            DailyGuidanceCache.language == language,
        )
        .first()
    )
    if row:
        row.payload = payload
        row.computed_at = datetime.utcnow()
        for key, val in fields.items():
            setattr(row, key, val)
    else:
        row = DailyGuidanceCache(
            kundli_id=kundli_id, local_date=local_date, conventions_hash=conventions_hash,
            payload=payload, language=language, **fields,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_audio_render(db: Session, text_sha256: str, language: str = "en",
                     voice: str | None = None) -> AudioRender | None:
    return (
        db.query(AudioRender)
        .filter(
            AudioRender.text_sha256 == text_sha256,
            AudioRender.language == language,
            AudioRender.voice == voice,
        )
        .first()
    )


def put_audio_render(db: Session, text_sha256: str, language: str = "en",
                     voice: str | None = None, **fields) -> AudioRender:
    row = get_audio_render(db, text_sha256, language, voice)
    if row:
        for key, val in fields.items():
            setattr(row, key, val)
    else:
        row = AudioRender(text_sha256=text_sha256, language=language, voice=voice, **fields)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_share_asset(db: Session, user_id: str, kind: str, **fields) -> ShareAsset:
    asset = ShareAsset(user_id=user_id, kind=kind, **fields)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


# ── Learning layer ────────────────────────────────────────────────────────────

def get_glossary_term(db: Session, slug: str, language: str = "en") -> GlossaryTerm | None:
    term = (
        db.query(GlossaryTerm)
        .filter(GlossaryTerm.slug == slug, GlossaryTerm.language == language)
        .first()
    )
    # Fall back to English so a missing Telugu entry still renders something.
    if not term and language != "en":
        term = (
            db.query(GlossaryTerm)
            .filter(GlossaryTerm.slug == slug, GlossaryTerm.language == "en")
            .first()
        )
    return term
