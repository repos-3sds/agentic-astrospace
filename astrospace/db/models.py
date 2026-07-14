import uuid
from datetime import datetime
from sqlalchemy import Float, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship, mapped_column, Mapped
from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


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
    chart_style: Mapped[str] = mapped_column(String, default="south")
    ayanamsha: Mapped[str] = mapped_column(String, default="lahiri")
    node_type: Mapped[str] = mapped_column(String, default="mean")
    timezone_mode: Mapped[str] = mapped_column(String, default="browser")
    panchanga_place: Mapped[dict | None] = mapped_column(JSON)
    language: Mapped[str] = mapped_column(String, default="en")
    regional_format: Mapped[str] = mapped_column(String, default="en-IN")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
