import uuid
from datetime import date, datetime, time
from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    Float,
    Integer,
    JSON,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import relationship, mapped_column, Mapped
from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# Postgres gets a native text[]; SQLite (local-dev fallback) gets JSON, since
# SQLite has no array type and would fail to compile the DDL otherwise.
_StringArray = ARRAY(String).with_variant(JSON, "sqlite")
_UuidString = Uuid(as_uuid=False).with_variant(String, "sqlite")


class Kundli(Base):
    __tablename__ = "kundlis"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, default="local-dev-user", index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    relation: Mapped[str] = mapped_column(String, default="friend")
    birth_year: Mapped[int]
    birth_month: Mapped[int]
    birth_day: Mapped[int]
    birth_hour: Mapped[int] = mapped_column(default=12)
    birth_minute: Mapped[int] = mapped_column(default=0)
    birth_city: Mapped[str] = mapped_column(String, nullable=False)
    birth_nation: Mapped[str] = mapped_column(String, default="US")
    sun_sign: Mapped[str | None] = mapped_column(String)
    moon_sign: Mapped[str | None] = mapped_column(String)
    ascendant: Mapped[str | None] = mapped_column(String)
    chart_data: Mapped[dict | None] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)
    # Added by 20260725120000_create_mobile_app_schema.sql — persisted coords let
    # panchanga/muhurta be timezone-correct instead of re-resolved per request.
    birth_latitude: Mapped[float | None] = mapped_column(Float)
    birth_longitude: Mapped[float | None] = mapped_column(Float)
    birth_timezone: Mapped[str | None] = mapped_column(String)
    birth_state: Mapped[str | None] = mapped_column(String)
    birth_time_accuracy: Mapped[str] = mapped_column(String, default="exact")  # exact | approximate | unknown
    # 'prospect' = lightweight chart for a compatibility check; hidden from the
    # profile switcher.
    kind: Mapped[str] = mapped_column(String, default="profile")  # profile | prospect
    archived_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    readings: Mapped[list["Reading"]] = relationship(
        "Reading", back_populates="kundli", cascade="all, delete-orphan",
        order_by="Reading.generated_at.desc()"
    )
    prediction_claims: Mapped[list["PredictionClaim"]] = relationship(
        "PredictionClaim", back_populates="kundli", cascade="all, delete-orphan",
        order_by="PredictionClaim.target_start_date.desc()"
    )


class Reading(Base):
    __tablename__ = "readings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    kundli_id: Mapped[str] = mapped_column(String, ForeignKey("kundlis.id"), nullable=False)
    reading_type: Mapped[str] = mapped_column(String, nullable=False)
    period_label: Mapped[str | None] = mapped_column(String)
    generated_local_date: Mapped[str | None] = mapped_column(String)
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_reading_id: Mapped[str | None] = mapped_column(String, ForeignKey("readings.id"))
    deviation_score: Mapped[float | None] = mapped_column(Float)
    deviation_summary: Mapped[dict | None] = mapped_column(JSON)
    user_rating: Mapped[int | None] = mapped_column(Integer)
    user_feedback: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String, default="en")
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    kundli: Mapped["Kundli"] = relationship("Kundli", back_populates="readings")
    claims: Mapped[list["PredictionClaim"]] = relationship(
        "PredictionClaim", back_populates="reading", cascade="all, delete-orphan",
        order_by="PredictionClaim.created_at.asc()"
    )


class PredictionClaim(Base):
    __tablename__ = "prediction_claims"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    kundli_id: Mapped[str] = mapped_column(String, ForeignKey("kundlis.id"), nullable=False, index=True)
    reading_id: Mapped[str] = mapped_column(String, ForeignKey("readings.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String, default="local-dev-user", index=True)
    reading_type: Mapped[str] = mapped_column(String, nullable=False)
    period_label: Mapped[str | None] = mapped_column(String)
    generated_local_date: Mapped[str | None] = mapped_column(String, index=True)
    target_start_date: Mapped[str | None] = mapped_column(String, index=True)
    target_end_date: Mapped[str | None] = mapped_column(String, index=True)
    category: Mapped[str] = mapped_column(String, default="general", index=True)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    source_excerpt: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    user_feedback: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    kundli: Mapped["Kundli"] = relationship("Kundli", back_populates="prediction_claims")
    reading: Mapped["Reading"] = relationship("Reading", back_populates="claims")


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    # 'eastern' is the mobile default; the DB CHECK constraint was widened to
    # allow it in 20260725120000 (it previously permitted only south|north).
    chart_style: Mapped[str] = mapped_column(String, default="eastern")
    ayanamsha: Mapped[str] = mapped_column(String, default="lahiri")
    node_type: Mapped[str] = mapped_column(String, default="mean")
    timezone_mode: Mapped[str] = mapped_column(String, default="browser")
    panchanga_place: Mapped[dict | None] = mapped_column(JSON)
    language: Mapped[str] = mapped_column(String, default="en")
    regional_format: Mapped[str] = mapped_column(String, default="en-IN")
    # Drives labels, nav priority, default disclosure and copy register app-wide.
    experience_mode: Mapped[str] = mapped_column(String, default="balanced")  # guided | balanced | practitioner
    tone: Mapped[str] = mapped_column(String, default="gentle")  # gentle | direct
    large_tap_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    audio_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    reduce_motion: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# =============================================================================
# Mobile app schema — mirrors supabase/migrations/20260725120000_create_mobile_app_schema.sql
#
# Most ids are still modelled as String so the same models work against the
# SQLite local-dev fallback in database.py. Ask history uses SQLAlchemy's UUID
# type with string values because the live Postgres schema stores these columns
# as uuid. Timestamps follow the existing naive-UTC convention used by the four
# original tables.
# =============================================================================


# ── Profile & devices ─────────────────────────────────────────────────────────

class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String)
    avatar_url: Mapped[str | None] = mapped_column(String)
    locale: Mapped[str] = mapped_column(String, default="en")
    timezone: Mapped[str | None] = mapped_column(String)
    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserDevice(Base):
    __tablename__ = "user_devices"
    __table_args__ = (UniqueConstraint("user_id", "device_id", name="user_devices_user_id_device_id_key"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    device_id: Mapped[str] = mapped_column(String, nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False)  # ios | android | web
    model: Mapped[str | None] = mapped_column(String)
    os_version: Mapped[str | None] = mapped_column(String)
    app_version: Mapped[str | None] = mapped_column(String)
    locale: Mapped[str | None] = mapped_column(String)
    timezone: Mapped[str | None] = mapped_column(String)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ── Ask ───────────────────────────────────────────────────────────────────────

class AskThread(Base):
    __tablename__ = "ask_threads"

    id: Mapped[str] = mapped_column(_UuidString, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    kundli_id: Mapped[str] = mapped_column(String, ForeignKey("kundlis.id"), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages: Mapped[list["AskMessage"]] = relationship(
        "AskMessage", back_populates="thread", cascade="all, delete-orphan",
        order_by="AskMessage.created_at",
    )


class AskMessage(Base):
    __tablename__ = "ask_messages"
    # The deployed Postgres CHECK on refer_out_kind was absent here, so the
    # column was a bare String to SQLAlchemy and the test suite — which runs
    # on in-memory SQLite — could not see it. That is precisely how the
    # constraint drifted out of step with the application for weeks while
    # every test stayed green (ASK-001; see the 20260811090000 migration).
    # Declaring it on the model puts the same rule in front of the tests.
    __table_args__ = (
        CheckConstraint(
            "refer_out_kind IS NULL OR refer_out_kind IN "
            "('death', 'health', 'legal', 'money')",
            name="ask_messages_refer_out_kind_check",
        ),
    )

    id: Mapped[str] = mapped_column(_UuidString, primary_key=True, default=_uuid)
    thread_id: Mapped[str] = mapped_column(_UuidString, ForeignKey("ask_threads.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String, nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str | None] = mapped_column(String)
    evidence: Mapped[dict | None] = mapped_column(JSON, default=dict)
    # non-null => the answer referred out instead of predicting
    refer_out_kind: Mapped[str | None] = mapped_column(String)
    input_mode: Mapped[str] = mapped_column(String, default="text")  # text | voice | chip
    language: Mapped[str] = mapped_column(String, default="en")
    model: Mapped[str | None] = mapped_column(String)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    thread: Mapped["AskThread"] = relationship("AskThread", back_populates="messages")


# ── Remedies & muhurta ────────────────────────────────────────────────────────

class Remedy(Base):
    __tablename__ = "remedies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    remedy_type: Mapped[str] = mapped_column(String, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    applies_to: Mapped[dict | None] = mapped_column(JSON, default=dict)
    tradition_source: Mapped[str | None] = mapped_column(String)
    default_target_count: Mapped[int | None] = mapped_column(Integer)
    cadence: Mapped[str | None] = mapped_column(String)
    is_convention_dependent: Mapped[bool] = mapped_column(Boolean, default=True)
    language: Mapped[str] = mapped_column(String, default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserRemedy(Base):
    __tablename__ = "user_remedies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    kundli_id: Mapped[str] = mapped_column(String, ForeignKey("kundlis.id"), nullable=False, index=True)
    remedy_id: Mapped[str] = mapped_column(String, ForeignKey("remedies.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, default="active")
    target_count: Mapped[int | None] = mapped_column(Integer)
    cadence: Mapped[str | None] = mapped_column(String)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    reminder_time: Mapped[time | None] = mapped_column(Time)
    reminder_weekday: Mapped[int | None] = mapped_column(SmallInteger)
    timezone: Mapped[str | None] = mapped_column(String)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    remedy: Mapped["Remedy"] = relationship("Remedy")
    completions: Mapped[list["RemedyCompletion"]] = relationship(
        "RemedyCompletion", back_populates="user_remedy", cascade="all, delete-orphan",
        order_by="RemedyCompletion.occurred_on.desc()",
    )


class RemedyCompletion(Base):
    """One row per day the practice was done; streaks are derived from these."""

    __tablename__ = "remedy_completions"
    __table_args__ = (
        UniqueConstraint("user_remedy_id", "occurred_on", name="remedy_completions_user_remedy_id_occurred_on_key"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_remedy_id: Mapped[str] = mapped_column(String, ForeignKey("user_remedies.id"), nullable=False, index=True)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user_remedy: Mapped["UserRemedy"] = relationship("UserRemedy", back_populates="completions")


class MuhurtaGoal(Base):
    __tablename__ = "muhurta_goals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    rules: Mapped[dict | None] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MuhurtaRequest(Base):
    __tablename__ = "muhurta_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    kundli_id: Mapped[str] = mapped_column(String, ForeignKey("kundlis.id"), nullable=False, index=True)
    goal_slug: Mapped[str] = mapped_column(String, nullable=False)
    free_text_goal: Mapped[str | None] = mapped_column(Text)
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    place: Mapped[dict | None] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String, default="pending")
    results: Mapped[list | None] = mapped_column(JSON, default=list)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SavedMuhurta(Base):
    __tablename__ = "saved_muhurtas"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    kundli_id: Mapped[str] = mapped_column(String, ForeignKey("kundlis.id"), nullable=False, index=True)
    request_id: Mapped[str | None] = mapped_column(String, ForeignKey("muhurta_requests.id"))
    goal_slug: Mapped[str | None] = mapped_column(String)
    label: Mapped[str | None] = mapped_column(String)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    quality: Mapped[str | None] = mapped_column(String)
    why: Mapped[dict | None] = mapped_column(JSON, default=dict)
    device_calendar_event_id: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ── Festivals & observances ───────────────────────────────────────────────────

class Festival(Base):
    __tablename__ = "festivals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    name_local: Mapped[str | None] = mapped_column(String)
    language: Mapped[str] = mapped_column(String, default="en")
    region: Mapped[str | None] = mapped_column(String)
    tradition: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    prep_guidance: Mapped[str | None] = mapped_column(Text)
    panchanga_rule: Mapped[dict | None] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FestivalOccurrence(Base):
    __tablename__ = "festival_occurrences"
    __table_args__ = (
        UniqueConstraint("festival_id", "occurs_on", "place_key",
                         name="festival_occurrences_festival_id_occurs_on_place_key_key"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    festival_id: Mapped[str] = mapped_column(String, ForeignKey("festivals.id"), nullable=False, index=True)
    occurs_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    place_key: Mapped[str] = mapped_column(String, default="default")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime)
    best_window: Mapped[dict | None] = mapped_column(JSON)
    computed_meta: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    festival: Mapped["Festival"] = relationship("Festival")


class UserObservance(Base):
    __tablename__ = "user_observances"
    __table_args__ = (
        UniqueConstraint("user_id", "festival_id", "occurs_on",
                         name="user_observances_user_id_festival_id_occurs_on_key"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    kundli_id: Mapped[str | None] = mapped_column(String, ForeignKey("kundlis.id"))
    festival_id: Mapped[str] = mapped_column(String, ForeignKey("festivals.id"), nullable=False)
    occurs_on: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String, default="planned")
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    reminder_lead_days: Mapped[int] = mapped_column(SmallInteger, default=2)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    festival: Mapped["Festival"] = relationship("Festival")


# ── Compatibility ─────────────────────────────────────────────────────────────

class CompatibilityCheck(Base):
    __tablename__ = "compatibility_checks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    kundli_id: Mapped[str] = mapped_column(String, ForeignKey("kundlis.id"), nullable=False)
    partner_kundli_id: Mapped[str] = mapped_column(String, ForeignKey("kundlis.id"), nullable=False)
    total_score: Mapped[float | None] = mapped_column(Numeric(4, 1))
    max_score: Mapped[float] = mapped_column(Numeric(4, 1), default=36)
    koota_breakdown: Mapped[dict | None] = mapped_column(JSON, default=dict)
    dosha_flags: Mapped[dict | None] = mapped_column(JSON, default=dict)
    verdict: Mapped[str | None] = mapped_column(Text)
    conventions: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    kundli: Mapped["Kundli"] = relationship("Kundli", foreign_keys=[kundli_id])
    partner: Mapped["Kundli"] = relationship("Kundli", foreign_keys=[partner_kundli_id])


# ── Notifications & alerts ────────────────────────────────────────────────────

class PushToken(Base):
    __tablename__ = "push_tokens"
    __table_args__ = (UniqueConstraint("provider", "token", name="push_tokens_provider_token_key"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    device_id: Mapped[str | None] = mapped_column(String, ForeignKey("user_devices.id"))
    provider: Mapped[str] = mapped_column(String, nullable=False)  # apns | fcm | webpush
    token: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[str] = mapped_column(String, default="production")
    locale: Mapped[str | None] = mapped_column(String)
    timezone: Mapped[str | None] = mapped_column(String)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NotificationPreference(Base):
    """One row per user per category — mirrors the Settings > Notifications screen."""

    __tablename__ = "notification_preferences"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    category: Mapped[str] = mapped_column(String, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    channels: Mapped[list | None] = mapped_column(_StringArray, default=lambda: ["push", "in_app"])
    lead_time_minutes: Mapped[int | None] = mapped_column(Integer)
    lead_time_days: Mapped[int | None] = mapped_column(SmallInteger)
    preferred_time: Mapped[time | None] = mapped_column(Time)
    quiet_hours_start: Mapped[time | None] = mapped_column(Time)
    quiet_hours_end: Mapped[time | None] = mapped_column(Time)
    timezone: Mapped[str | None] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationJob(Base):
    __tablename__ = "notification_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    kundli_id: Mapped[str | None] = mapped_column(String, ForeignKey("kundlis.id"))
    category: Mapped[str] = mapped_column(String, nullable=False)
    # e.g. 'morning_brief:<kundli>:2026-07-25' — prevents double sends
    dedupe_key: Mapped[str | None] = mapped_column(String, unique=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    timezone: Mapped[str | None] = mapped_column(String)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    deep_link: Mapped[str | None] = mapped_column(String)
    payload: Mapped[dict | None] = mapped_column(JSON, default=dict)
    language: Mapped[str] = mapped_column(String, default="en")
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    skip_reason: Mapped[str | None] = mapped_column(String)
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deliveries: Mapped[list["NotificationDelivery"]] = relationship(
        "NotificationDelivery", back_populates="job", cascade="all, delete-orphan",
    )


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("notification_jobs.id"), nullable=False, index=True)
    push_token_id: Mapped[str | None] = mapped_column(String, ForeignKey("push_tokens.id"))
    provider: Mapped[str | None] = mapped_column(String)
    provider_message_id: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="queued")
    status_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    error: Mapped[str | None] = mapped_column(Text)
    receipt: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped["NotificationJob"] = relationship("NotificationJob", back_populates="deliveries")


class UserAlert(Base):
    """In-app alert inbox. Severity is deliberately limited to info|attention —
    the product never uses fear framing (design_principles.md §4)."""

    __tablename__ = "user_alerts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    kundli_id: Mapped[str | None] = mapped_column(String, ForeignKey("kundlis.id"))
    category: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, default="info")
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    deep_link: Mapped[str | None] = mapped_column(String)
    source_job_id: Mapped[str | None] = mapped_column(String, ForeignKey("notification_jobs.id"))
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ── Native surfaces ───────────────────────────────────────────────────────────

class WidgetInstall(Base):
    __tablename__ = "widget_installs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    device_id: Mapped[str | None] = mapped_column(String, ForeignKey("user_devices.id"))
    kind: Mapped[str] = mapped_column(String, nullable=False)
    family: Mapped[str | None] = mapped_column(String)
    kundli_id: Mapped[str | None] = mapped_column(String, ForeignKey("kundlis.id"))
    settings: Mapped[dict | None] = mapped_column(JSON, default=dict)
    last_rendered_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LiveActivity(Base):
    __tablename__ = "live_activities"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    device_id: Mapped[str | None] = mapped_column(String, ForeignKey("user_devices.id"))
    kundli_id: Mapped[str | None] = mapped_column(String, ForeignKey("kundlis.id"))
    kind: Mapped[str] = mapped_column(String, nullable=False)
    activity_token: Mapped[str | None] = mapped_column(Text)
    push_to_start_token: Mapped[str | None] = mapped_column(Text)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    state: Mapped[dict | None] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Caches ────────────────────────────────────────────────────────────────────

class DailyGuidanceCache(Base):
    """Backs the offline-first Today card. conventions_hash keys the row to the
    ayanamsha/node/place used, so changing a convention invalidates it."""

    __tablename__ = "daily_guidance_cache"
    __table_args__ = (
        UniqueConstraint("kundli_id", "local_date", "conventions_hash", "language",
                         name="daily_guidance_cache_kundli_date_conv_lang_key"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    kundli_id: Mapped[str] = mapped_column(String, ForeignKey("kundlis.id"), nullable=False, index=True)
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    conventions_hash: Mapped[str] = mapped_column(String, nullable=False)
    place: Mapped[dict | None] = mapped_column(JSON, default=dict)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    language: Mapped[str] = mapped_column(String, default="en")
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)


class AudioRender(Base):
    __tablename__ = "audio_renders"
    __table_args__ = (
        UniqueConstraint("text_sha256", "language", "voice", name="audio_renders_text_sha256_language_voice_key"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(String, index=True)
    kundli_id: Mapped[str | None] = mapped_column(String, ForeignKey("kundlis.id"))
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[str | None] = mapped_column(String)
    text_sha256: Mapped[str] = mapped_column(String, nullable=False)
    language: Mapped[str] = mapped_column(String, default="en")
    voice: Mapped[str | None] = mapped_column(String)
    tone: Mapped[str | None] = mapped_column(String)
    storage_bucket: Mapped[str | None] = mapped_column(String)
    storage_path: Mapped[str | None] = mapped_column(String)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, default="ready")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)


class ShareAsset(Base):
    __tablename__ = "share_assets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    kundli_id: Mapped[str | None] = mapped_column(String, ForeignKey("kundlis.id"))
    kind: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, default=dict)
    storage_bucket: Mapped[str | None] = mapped_column(String)
    storage_path: Mapped[str | None] = mapped_column(String)
    share_token: Mapped[str | None] = mapped_column(String, unique=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ── Learning layer ────────────────────────────────────────────────────────────

class GlossaryTerm(Base):
    __tablename__ = "glossary_terms"
    __table_args__ = (UniqueConstraint("slug", "language", name="glossary_terms_slug_language_key"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String, nullable=False, index=True)
    language: Mapped[str] = mapped_column(String, default="en")
    term: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str | None] = mapped_column(String)
    plain_definition: Mapped[str] = mapped_column(Text, nullable=False)
    classical_rule: Mapped[str | None] = mapped_column(Text)
    source_citation: Mapped[str | None] = mapped_column(String)
    verse: Mapped[str | None] = mapped_column(Text)
    is_convention_dependent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
