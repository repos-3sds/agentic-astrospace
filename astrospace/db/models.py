import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship, mapped_column, Mapped
from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Kundli(Base):
    __tablename__ = "kundlis"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    relation: Mapped[str] = mapped_column(String, default="friend")
    birth_year: Mapped[int]
    birth_month: Mapped[int]
    birth_day: Mapped[int]
    birth_hour: Mapped[int] = mapped_column(default=12)
    birth_minute: Mapped[int] = mapped_column(default=0)
    birth_city: Mapped[str] = mapped_column(String, nullable=False)
    birth_nation: Mapped[str] = mapped_column(String, default="US")
    sun_sign: Mapped[Optional[str]] = mapped_column(String)
    moon_sign: Mapped[Optional[str]] = mapped_column(String)
    ascendant: Mapped[Optional[str]] = mapped_column(String)
    chart_data: Mapped[Optional[dict]] = mapped_column(JSON)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    readings: Mapped[List["Reading"]] = relationship(
        "Reading", back_populates="kundli", cascade="all, delete-orphan",
        order_by="Reading.generated_at.desc()"
    )


class Reading(Base):
    __tablename__ = "readings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    kundli_id: Mapped[str] = mapped_column(String, ForeignKey("kundlis.id"), nullable=False)
    reading_type: Mapped[str] = mapped_column(String, nullable=False)
    period_label: Mapped[Optional[str]] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    kundli: Mapped["Kundli"] = relationship("Kundli", back_populates="readings")
