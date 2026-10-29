"""The signed-in user's own surface: profile, devices, notifications, alerts.

Everything here is scoped to the caller. `user_id` is taken from the resolved
bearer token and never from the request body, so a client cannot address
another user's rows by asking nicely.

Two CRUD helpers underneath are deliberately id-only and carry no ownership
filter (`revoke_push_token`, `end_live_activity`). They are reachable from the
delivery worker as well as from here, so the ownership check lives in this
layer — see `_owned_push_token` and the live-activity handler.
"""
from datetime import date as date_cls, datetime, time as time_cls
import logging
import os
from urllib.parse import quote
import requests

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import crud, crud_mobile as cm, get_db
from ..db.models import (
    AnswerReport, AskThread, AudioRender, BillingAccount, CompatibilityCheck, CompatibilityInsight, DailyGuidanceCache, EmailRecipient,
    EntitlementAuditEvent, EntitlementOverride, Kundli,
    LifeStory, LiveActivity, MuhurtaRequest, NotificationJob, NotificationPreference,
    PlanAssignment, PushToken, QuestionCredit, SavedMuhurta, ShareAsset, SubscriptionGrant,
    UsageBucket, UserAlert, UserDevice, UserObservance,
    UserProfile, UserRemedy, UserSettings, WidgetInstall,
    ProfileContextAuditEvent, ProfileContextFact, ProfileContextLedger,
    ProfileContextMutation, AskMessage, RemedyCompletion,
)
from ..admin.audit_middleware import pseudonymous_actor_id
from ..admin.client import get_admin_client
from ..entitlements import razorpay
from .auth import CurrentUser

router = APIRouter(prefix="/api/v1/me", tags=["me"])
log = logging.getLogger(__name__)

# Severity is capped at "attention" in the schema on purpose: the product does
# not have a "critical" or "danger" tier. Mirrored here so a bad payload is
# rejected at the edge rather than by a constraint violation.
ALERT_SEVERITIES = {"info", "attention"}


# ── Payloads ─────────────────────────────────────────────────────────────────

# Free-text fields had no upper bound (audit S17).
_TOKEN_MAX = 4096
_URL_MAX = 2048
_SHORT_MAX = 100


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=200)
    avatar_url: str | None = Field(None, max_length=_URL_MAX)
    locale: str | None = Field(None, max_length=35)
    timezone: str | None = Field(None, max_length=64)
    marketing_opt_in: bool | None = None


class DeviceRegistration(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=200)
    platform: str = Field(..., pattern="^(ios|android|web)$")
    model: str | None = Field(None, max_length=_SHORT_MAX)
    os_version: str | None = Field(None, max_length=_SHORT_MAX)
    app_version: str | None = Field(None, max_length=_SHORT_MAX)
    locale: str | None = Field(None, max_length=35)
    timezone: str | None = Field(None, max_length=64)


class PushTokenRegistration(BaseModel):
    provider: str = Field(..., pattern="^(apns|fcm|web)$")
    token: str = Field(..., min_length=1, max_length=_TOKEN_MAX)
    device_id: str | None = Field(None, max_length=200)
    environment: str = Field("production", pattern="^(production|sandbox)$")
    locale: str | None = Field(None, max_length=35)
    timezone: str | None = Field(None, max_length=64)
    # The build the phone is running, so update reminders reach only the
    # phones still behind (notifications/app_updates.py).
    app_build: int | None = Field(None, ge=0, le=10_000_000)
    # The token this device registered before, when the OS has since rotated
    # it. Both stay deliverable for a while, so without this every push went
    # out twice to the same phone (retest of build 487).
    replaces: str | None = Field(None, max_length=_TOKEN_MAX)


class PushTokenRevocation(BaseModel):
    provider: str = Field(..., pattern="^(apns|fcm|web)$")
    token: str = Field(..., min_length=1, max_length=_TOKEN_MAX)


class NotificationPreferenceUpdate(BaseModel):
    enabled: bool | None = None
    channels: list[str] | None = None
    lead_time_minutes: int | None = Field(None, ge=0, le=1440)
    lead_time_days: int | None = Field(None, ge=0, le=30)
    # Accepted as "HH:MM"; the columns are SQL TIME, and pydantic parses the
    # string into a time for us. Emitted back as "HH:MM" by _hhmm below.
    preferred_time: time_cls | None = None
    quiet_hours_start: time_cls | None = None
    quiet_hours_end: time_cls | None = None
    timezone: str | None = None


class LiveActivityStart(BaseModel):
    kind: str = Field(..., min_length=1, max_length=64)
    starts_at: datetime
    ends_at: datetime
    device_id: str | None = Field(None, max_length=200)
    kundli_id: str | None = Field(None, max_length=64)
    activity_token: str | None = Field(None, max_length=_TOKEN_MAX)
    push_to_start_token: str | None = Field(None, max_length=_TOKEN_MAX)
    state: dict | None = None


class WidgetInstallPayload(BaseModel):
    kind: str = Field(..., min_length=1, max_length=64)
    family: str | None = Field(None, max_length=64)
    device_id: str | None = Field(None, max_length=200)
    kundli_id: str | None = Field(None, max_length=64)
    settings: dict | None = None


class AccountDeletionPayload(BaseModel):
    confirmation: str


# ── Serialisers ──────────────────────────────────────────────────────────────

def _profile(row) -> dict:
    return {
        "user_id": row.user_id,
        "display_name": row.display_name,
        "avatar_url": row.avatar_url,
        "locale": row.locale,
        "timezone": row.timezone,
        "marketing_opt_in": row.marketing_opt_in,
    }


def _hhmm(value):
    """SQL TIME values go out as "HH:MM" — the same shape the client sends."""
    return value.strftime("%H:%M") if isinstance(value, time_cls) else value


def _prefs(raw: dict) -> dict:
    return {
        category: {k: _hhmm(v) for k, v in values.items()}
        for category, values in raw.items()
    }


def _alert(row) -> dict:
    return {
        "id": row.id,
        "category": row.category,
        "severity": row.severity,
        "title": row.title,
        "body": row.body,
        "deep_link": row.deep_link,
        "kundli_id": row.kundli_id,
        "read_at": row.read_at.isoformat() if row.read_at else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


# ── Profile & devices ────────────────────────────────────────────────────────

@router.get("")
def get_profile(user: CurrentUser, db: Session = Depends(get_db)):
    """The profile is created on first read, so the app never 404s on itself."""
    return _profile(cm.get_or_create_user_profile(db, user.id))


@router.patch("")
def patch_profile(payload: ProfileUpdate, user: CurrentUser,
                  db: Session = Depends(get_db)):
    cm.get_or_create_user_profile(db, user.id)
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    return _profile(cm.update_user_profile(db, user.id, data))


# Columns never handed out, even to their owner: credentials and tokens that
# act on the account rather than describe it.
_EXPORT_REDACT = {"token", "unsubscribe_token", "secret", "push_token", "device_token"}


def _export_rows(rows) -> list[dict]:
    out = []
    for row in rows:
        item = {}
        for column in row.__table__.columns:
            if column.key in _EXPORT_REDACT or column.key.endswith("_token"):
                continue
            value = getattr(row, column.key)
            if isinstance(value, (datetime, date_cls, time_cls)):
                value = value.isoformat()
            elif isinstance(value, (bytes, bytearray)):
                value = None
            item[column.key] = value
        out.append(item)
    return out


@router.get("/export")
def export_account(user: CurrentUser, db: Session = Depends(get_db)):
    """Everything this account holds, as JSON (usability audit U9).

    The deletion screen names profiles, questions, readings, notes, settings
    and practice counts as the reader's data; the export used to carry only
    profiles. Billing ledgers stay out (they are store records, not the
    reader's content), and so do tokens.
    """
    kundlis = db.query(Kundli).filter(Kundli.user_id == user.id).all()
    kundli_ids = [row.id for row in kundlis]
    threads = db.query(AskThread).filter(AskThread.user_id == user.id).all()
    thread_ids = [row.id for row in threads]
    remedies = db.query(UserRemedy).filter(UserRemedy.user_id == user.id).all()
    remedy_ids = [row.id for row in remedies]
    by_user = lambda model: db.query(model).filter(model.user_id == user.id).all()  # noqa: E731
    return {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "account": {"id": user.id, "email": user.email},
        "profile": _export_rows(by_user(UserProfile)),
        "settings": _export_rows(by_user(UserSettings)),
        "profiles": _export_rows(kundlis),
        "ask_threads": _export_rows(threads),
        "ask_messages": _export_rows(
            db.query(AskMessage).filter(AskMessage.thread_id.in_(thread_ids)).all()
        ) if thread_ids else [],
        "remedies": _export_rows(remedies),
        "remedy_completions": _export_rows(
            db.query(RemedyCompletion).filter(RemedyCompletion.user_remedy_id.in_(remedy_ids)).all()
        ) if remedy_ids else [],
        "saved_muhurtas": _export_rows(by_user(SavedMuhurta)),
        "muhurta_requests": _export_rows(by_user(MuhurtaRequest)),
        "compatibility_checks": _export_rows(by_user(CompatibilityCheck)),
        "compatibility_insights": _export_rows(by_user(CompatibilityInsight)),
        "life_stories": _export_rows(by_user(LifeStory)),
        "answer_reports": _export_rows(by_user(AnswerReport)),
        "observances": _export_rows(by_user(UserObservance)),
        "alerts": _export_rows(by_user(UserAlert)),
        "notification_preferences": _export_rows(by_user(NotificationPreference)),
        "email": _export_rows(by_user(EmailRecipient)),
        "memory": _export_rows(
            db.query(ProfileContextFact).filter(ProfileContextFact.profile_id.in_(kundli_ids)).all()
        ) if kundli_ids else [],
    }


@router.delete("")
def delete_account(payload: AccountDeletionPayload, user: CurrentUser,
                   db: Session = Depends(get_db)):
    """Permanently remove the caller's app data and Supabase identity.

    The typed confirmation is checked by the backend; a client cannot bypass
    it by calling the endpoint directly. Auth deletion requires the service
    role.

    Order matters. The app data is committed first, then the Supabase auth
    user is deleted (with one retry). It used to be the other way round: an
    auth deletion followed by a failed commit left a person with no way to
    sign in and all of their data still stored. Now the worst case is data
    gone and the sign-in still present — and calling this again finishes the
    job, because every database step is a no-op the second time.

    The request audit log keeps every mutating request this person made;
    their email is erased from it and their id replaced by a pseudonym
    (`_erase_request_audit`), and the audit row for this request is written
    without the email (see AppAuditMiddleware).
    """
    if payload.confirmation.strip().casefold() != "delete":
        raise HTTPException(status_code=400, detail="Type DELETE to confirm")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if user.auth_enabled and not service_key:
        raise HTTPException(status_code=503, detail="Account deletion is not configured")

    kundli_ids = [row.id for row in db.query(Kundli).filter(Kundli.user_id == user.id)]

    # Children before parents where the schema does not declare ON DELETE.
    db.query(UserAlert).filter(UserAlert.user_id == user.id).delete(synchronize_session=False)
    for row in db.query(NotificationJob).filter(NotificationJob.user_id == user.id).all():
        db.delete(row)  # ORM cascade removes delivery attempts.
    db.flush()
    db.query(PushToken).filter(PushToken.user_id == user.id).delete(synchronize_session=False)
    db.query(SavedMuhurta).filter(SavedMuhurta.user_id == user.id).delete(synchronize_session=False)
    db.query(MuhurtaRequest).filter(MuhurtaRequest.user_id == user.id).delete(synchronize_session=False)
    # Reports point at Ask messages, so they go first.
    db.query(AnswerReport).filter(AnswerReport.user_id == user.id).delete(synchronize_session=False)
    for row in db.query(AskThread).filter(AskThread.user_id == user.id).all():
        db.delete(row)
    for row in db.query(UserRemedy).filter(UserRemedy.user_id == user.id).all():
        db.delete(row)

    for model in (
        CompatibilityCheck, CompatibilityInsight, LifeStory, UserObservance, WidgetInstall, LiveActivity,
        AudioRender, ShareAsset, NotificationPreference, EmailRecipient,
    ):
        db.query(model).filter(model.user_id == user.id).delete(synchronize_session=False)
    if kundli_ids:
        for model in (
            ProfileContextAuditEvent, ProfileContextMutation,
            ProfileContextFact, ProfileContextLedger,
        ):
            db.query(model).filter(model.profile_id.in_(kundli_ids)).delete(
                synchronize_session=False
            )
        db.query(DailyGuidanceCache).filter(
            DailyGuidanceCache.kundli_id.in_(kundli_ids)
        ).delete(synchronize_session=False)
    for row in db.query(Kundli).filter(Kundli.user_id == user.id).all():
        db.delete(row)
    db.query(UserSettings).filter(UserSettings.user_id == user.id).delete(synchronize_session=False)
    db.query(UserProfile).filter(UserProfile.user_id == user.id).delete(synchronize_session=False)
    # Stop any website subscription before its records go (best effort).
    razorpay.cancel_for_deleted_account(db, user.id)
    # CE-2 creates a Free billing account on first entitlement resolution. No
    # store transactions exist yet, so delete the complete commercial
    # foundation record. CE-3 must replace this with the approved legal/audit
    # retention policy before verified provider records can be written.
    for account in db.query(BillingAccount).filter(BillingAccount.owner_user_id == user.id).all():
        for model in (
            UsageBucket, QuestionCredit, EntitlementOverride, PlanAssignment,
            SubscriptionGrant, EntitlementAuditEvent,
        ):
            db.query(model).filter(model.billing_account_id == account.id).delete(
                synchronize_session=False
            )
        db.delete(account)
    db.flush()
    db.query(UserDevice).filter(UserDevice.user_id == user.id).delete(synchronize_session=False)
    db.commit()

    _erase_request_audit(user.id)
    _delete_store_customer(user.id)

    if user.auth_enabled and not _delete_auth_user(user.id, service_key):
        # The data is already gone; only the sign-in remains. A retry of this
        # endpoint completes the deletion.
        raise HTTPException(
            status_code=502,
            detail="Your data was deleted, but your sign-in could not be removed. "
                   "Please try again.",
        )
    return {"deleted": True}


AUTH_DELETE_ATTEMPTS = 2  # the first try plus one retry


def _delete_auth_user(user_id: str, service_key: str) -> bool:
    """Delete the Supabase auth user. True when it is gone (a 404 counts: a
    retried deletion may find it already removed)."""
    url = f"{os.environ['SUPABASE_URL'].rstrip('/')}/auth/v1/admin/users/{user_id}"
    headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}
    for attempt in range(1, AUTH_DELETE_ATTEMPTS + 1):
        try:
            response = requests.delete(url, headers=headers, timeout=8)
        except requests.RequestException:
            log.exception("auth user deletion attempt %d failed", attempt)
            continue
        if response.status_code in {200, 204, 404}:
            return True
        log.error("auth user deletion attempt %d returned %d", attempt, response.status_code)
    return False


REVENUECAT_API = "https://api.revenuecat.com/v1/subscribers"


def _delete_store_customer(user_id: str) -> None:
    """Remove this person's RevenueCat customer, whose app_user_id is their
    Supabase id. Best effort, like the audit erasure: the store keeps its own
    receipts either way, and an outage must not block the deletion. Skipped
    until REVENUECAT_SECRET_API_KEY is set (no purchases are live yet)."""
    key = os.getenv("REVENUECAT_SECRET_API_KEY", "").strip()
    if not key:
        return
    try:
        response = requests.delete(
            f"{REVENUECAT_API}/{quote(user_id, safe='')}",
            headers={"Authorization": f"Bearer {key}"}, timeout=8,
        )
    except requests.RequestException:
        log.exception("store customer deletion failed; delete it in RevenueCat by hand")
        return
    if response.status_code not in {200, 204, 404}:
        log.error("store customer deletion returned %d; delete it in RevenueCat by hand",
                  response.status_code)


def _erase_request_audit(user_id: str) -> None:
    """Clear the email and pseudonymise the id on this person's rows in
    app_request_audit_log. Best effort: the log lives in Supabase (not on the
    ORM), and its outage must not block deleting the account itself — a
    failure is logged for follow-up instead."""
    try:
        get_admin_client().patch(
            "app_request_audit_log",
            params={"actor_id": f"eq.{user_id}"},
            payload={"actor_email": None, "actor_id": pseudonymous_actor_id(user_id)},
        )
    except Exception:
        log.exception("request audit erasure failed; erase actor rows manually")


@router.put("/devices")
def register_device(payload: DeviceRegistration, user: CurrentUser,
                    db: Session = Depends(get_db)):
    """Called on app launch; idempotent per (user, device_id)."""
    data = payload.model_dump(exclude={"device_id"}, exclude_none=True)
    device = cm.upsert_device(db, user.id, payload.device_id, data)
    return {"id": device.id, "device_id": device.device_id,
            "platform": device.platform,
            "last_seen_at": device.last_seen_at.isoformat()}


# ── Push tokens ──────────────────────────────────────────────────────────────

def _owned_push_token(db: Session, user_id: str, provider: str, token: str):
    """`revoke_push_token` filters on (provider, token) only, so check here.

    Without this a caller holding someone else's token string could silence
    their notifications.
    """
    return (
        db.query(PushToken)
        .filter(PushToken.provider == provider,
                PushToken.token == token,
                PushToken.user_id == user_id)
        .first()
    )


@router.put("/push-tokens")
def register_push_token(payload: PushTokenRegistration, user: CurrentUser,
                        db: Session = Depends(get_db)):
    row = cm.upsert_push_token(
        db, user.id, payload.provider, payload.token,
        **payload.model_dump(exclude={"provider", "token", "replaces"}, exclude_none=True),
    )
    if payload.replaces and payload.replaces != payload.token and _owned_push_token(
            db, user.id, payload.provider, payload.replaces):
        cm.revoke_push_token(db, payload.provider, payload.replaces)
    return {"id": row.id, "provider": row.provider,
            "environment": row.environment, "revoked_at": None}


@router.post("/push-tokens/revoke")
def revoke_push_token(payload: PushTokenRevocation, user: CurrentUser,
                      db: Session = Depends(get_db)):
    if not _owned_push_token(db, user.id, payload.provider, payload.token):
        raise HTTPException(status_code=404, detail="Push token not found")
    cm.revoke_push_token(db, payload.provider, payload.token)
    return {"revoked": True}


# One test per reader per window: a second tap inside it returns the queued
# job instead of stacking up pushes.
TEST_PUSH_WINDOW_MINUTES = 5


@router.post("/test-notification")
def send_test_notification(user: CurrentUser, db: Session = Depends(get_db)):
    """Settings > Notifications > "Send a test notification".

    Queues an ordinary notification job, due now, for this reader only. The
    worker delivers it on its next run like any other job, through the same
    transports (FCM, APNs) and the same per-token delivery records, so a test
    that arrives proves the real path end to end. The API itself holds no push
    credentials. 409 when this account has no phone registered for push.
    """
    tokens = cm.list_active_push_tokens(db, user.id)
    if not tokens:
        raise HTTPException(
            status_code=409,
            detail="No phone is registered for notifications on this account yet. "
                   "Open Siddha on your phone and allow notifications first.",
        )
    now = datetime.utcnow()
    window = int(now.timestamp()) // (TEST_PUSH_WINDOW_MINUTES * 60)
    job = cm.schedule_notification(
        db, user.id, "system", now,
        title="Test notification from Siddha",
        body="If you can read this, notifications reach this phone.",
        deep_link="/m/settings/notifications",
        dedupe_key=f"test_push:{user.id}:{window}",
        payload={"kind": "test"},
    )
    return {
        "id": job.id,
        "status": job.status,
        "devices": sorted({t.provider for t in tokens}),
        "within_minutes": 15,
    }


# ── Notification preferences ─────────────────────────────────────────────────

@router.get("/notification-preferences")
def get_notification_preferences(user: CurrentUser, db: Session = Depends(get_db)):
    """Stored rows merged over defaults, so every category always resolves."""
    return {"preferences": _prefs(cm.get_notification_preferences(db, user.id))}


@router.put("/notification-preferences/{category}")
def set_notification_preference(category: str,
                                payload: NotificationPreferenceUpdate,
                                user: CurrentUser,
                                db: Session = Depends(get_db)):
    if category not in cm.DEFAULT_NOTIFICATION_PREFS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown category {category!r}; expected one of "
                   f"{sorted(cm.DEFAULT_NOTIFICATION_PREFS)}",
        )
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    cm.set_notification_preference(db, user.id, category, **fields)
    return {"preferences": _prefs(cm.get_notification_preferences(db, user.id))}


# ── Alerts ───────────────────────────────────────────────────────────────────

@router.get("/alerts")
def list_alerts(user: CurrentUser,
                unread_only: bool = False,
                limit: int = Query(50, ge=1, le=200),
                db: Session = Depends(get_db)):
    rows = cm.list_alerts(db, user.id, unread_only=unread_only, limit=limit)
    return {
        "unread_count": cm.count_unread_alerts(db, user.id),
        "count": len(rows),
        "alerts": [_alert(r) for r in rows],
    }


@router.post("/alerts/{alert_id}/read")
def mark_alert_read(alert_id: str, user: CurrentUser, db: Session = Depends(get_db)):
    if not cm.mark_alert_read(db, alert_id, user.id):
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"read": True, "unread_count": cm.count_unread_alerts(db, user.id)}


@router.post("/alerts/{alert_id}/dismiss")
def dismiss_alert(alert_id: str, user: CurrentUser, db: Session = Depends(get_db)):
    if not cm.dismiss_alert(db, alert_id, user.id):
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"dismissed": True, "unread_count": cm.count_unread_alerts(db, user.id)}


# ── Native surfaces ──────────────────────────────────────────────────────────

def _require_own_kundli(db: Session, kundli_id: str | None, user_id: str) -> None:
    """A widget or live activity may name only the caller's own profile (S17)."""
    if kundli_id and not crud.get_kundli(db, kundli_id, user_id):
        raise HTTPException(status_code=404, detail="Kundli not found")


@router.post("/live-activities")
def start_live_activity(payload: LiveActivityStart, user: CurrentUser,
                        db: Session = Depends(get_db)):
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=400, detail="ends_at must be after starts_at")
    _require_own_kundli(db, payload.kundli_id, user.id)
    row = cm.start_live_activity(
        db, user.id, payload.kind, payload.starts_at, payload.ends_at,
        **payload.model_dump(exclude={"kind", "starts_at", "ends_at"},
                             exclude_none=True),
    )
    return {"id": row.id, "kind": row.kind, "status": row.status,
            "starts_at": row.starts_at.isoformat(),
            "ends_at": row.ends_at.isoformat()}


@router.get("/live-activities")
def list_live_activities(user: CurrentUser, db: Session = Depends(get_db)):
    rows = cm.list_active_live_activities(db, user.id)
    return {"count": len(rows), "activities": [
        {"id": r.id, "kind": r.kind, "status": r.status,
         "starts_at": r.starts_at.isoformat(), "ends_at": r.ends_at.isoformat(),
         "state": r.state}
        for r in rows
    ]}


@router.post("/live-activities/{activity_id}/end")
def end_live_activity(activity_id: str, user: CurrentUser,
                      status: str = Query("ended", pattern="^(ended|stale)$"),
                      db: Session = Depends(get_db)):
    # end_live_activity() looks up by id alone, so confirm ownership first.
    owned = (
        db.query(LiveActivity)
        .filter(LiveActivity.id == activity_id, LiveActivity.user_id == user.id)
        .first()
    )
    if not owned:
        raise HTTPException(status_code=404, detail="Live activity not found")
    cm.end_live_activity(db, activity_id, status)
    return {"ended": True, "status": status}


@router.post("/widgets")
def install_widget(payload: WidgetInstallPayload, user: CurrentUser,
                   db: Session = Depends(get_db)):
    _require_own_kundli(db, payload.kundli_id, user.id)
    row = cm.upsert_widget_install(
        db, user.id, payload.kind,
        **payload.model_dump(exclude={"kind"}, exclude_none=True),
    )
    return {"id": row.id, "kind": row.kind, "family": row.family,
            "settings": row.settings}
