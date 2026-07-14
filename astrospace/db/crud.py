from datetime import datetime
from sqlalchemy.orm import Session
from .models import Kundli, PredictionClaim, Reading, UserSettings


# ── Kundli ────────────────────────────────────────────────────────────────────

def create_kundli(db: Session, data: dict) -> Kundli:
    k = Kundli(**data)
    db.add(k)
    db.commit()
    db.refresh(k)
    return k


def get_kundli(db: Session, kundli_id: str, user_id: str | None = None) -> Kundli | None:
    q = db.query(Kundli).filter(Kundli.id == kundli_id)
    if user_id is not None:
        q = q.filter(Kundli.user_id == user_id)
    return q.first()


def list_kundlis(db: Session, user_id: str | None = None) -> list[Kundli]:
    q = db.query(Kundli)
    if user_id is not None:
        q = q.filter(Kundli.user_id == user_id)
    return q.order_by(Kundli.name).all()


def count_kundlis(db: Session, user_id: str) -> int:
    return db.query(Kundli).filter(Kundli.user_id == user_id).count()


def transfer_kundlis(db: Session, from_user_id: str, to_user_id: str) -> int:
    rows = db.query(Kundli).filter(Kundli.user_id == from_user_id).all()
    for row in rows:
        row.user_id = to_user_id
    db.commit()
    return len(rows)


def update_kundli(
    db: Session, kundli_id: str, data: dict, user_id: str | None = None
) -> Kundli | None:
    k = get_kundli(db, kundli_id, user_id)
    if not k:
        return None
    for key, val in data.items():
        setattr(k, key, val)
    db.commit()
    db.refresh(k)
    return k


def delete_kundli(db: Session, kundli_id: str, user_id: str | None = None) -> bool:
    k = get_kundli(db, kundli_id, user_id)
    if not k:
        return False
    db.delete(k)
    db.commit()
    return True


# ── Reading ───────────────────────────────────────────────────────────────────

def save_reading(
    db: Session,
    kundli_id: str,
    reading_type: str,
    content: str,
    period_label: str = None,
    generated_local_date: str = None,
    version: int = 1,
    parent_reading_id: str = None,
    deviation_score: float = None,
    deviation_summary: dict = None,
) -> Reading:
    r = Reading(
        kundli_id=kundli_id,
        reading_type=reading_type,
        content=content,
        period_label=period_label,
        generated_local_date=generated_local_date,
        version=version,
        parent_reading_id=parent_reading_id,
        deviation_score=deviation_score,
        deviation_summary=deviation_summary,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def get_readings(
    db: Session,
    kundli_id: str,
    user_id: str | None = None,
    reading_type: str = None,
    period_label: str = None,
    generated_local_date: str = None,
    limit: int = 50,
) -> list[Reading]:
    q = db.query(Reading).filter(Reading.kundli_id == kundli_id)
    if user_id is not None:
        q = q.join(Kundli).filter(Kundli.user_id == user_id)
    if reading_type:
        q = q.filter(Reading.reading_type == reading_type)
    if period_label:
        q = q.filter(Reading.period_label == period_label)
    if generated_local_date:
        q = q.filter(Reading.generated_local_date == generated_local_date)
    return q.order_by(Reading.generated_at.desc()).limit(limit).all()


def get_readings_for_calendar(
    db: Session,
    kundli_id: str,
    user_id: str | None,
    start_date: str,
    end_date: str,
    limit: int = 200,
) -> list[Reading]:
    q = db.query(Reading).filter(Reading.kundli_id == kundli_id)
    if user_id is not None:
        q = q.join(Kundli).filter(Kundli.user_id == user_id)
    return (
        q.filter(Reading.generated_local_date >= start_date)
         .filter(Reading.generated_local_date <= end_date)
         .order_by(Reading.generated_local_date.asc(), Reading.version.desc(), Reading.generated_at.desc())
         .limit(limit)
         .all()
    )


def get_reading(
    db: Session,
    kundli_id: str,
    reading_id: str,
    user_id: str | None = None,
) -> Reading | None:
    q = db.query(Reading).filter(Reading.kundli_id == kundli_id, Reading.id == reading_id)
    if user_id is not None:
        q = q.join(Kundli).filter(Kundli.user_id == user_id)
    return q.first()


def get_latest_reading(
    db: Session,
    kundli_id: str,
    reading_type: str,
    user_id: str | None = None,
) -> Reading | None:
    q = db.query(Reading).filter(Reading.kundli_id == kundli_id, Reading.reading_type == reading_type)
    if user_id is not None:
        q = q.join(Kundli).filter(Kundli.user_id == user_id)
    return q.order_by(Reading.generated_at.desc()).first()


def get_latest_period_reading(
    db: Session,
    kundli_id: str,
    reading_type: str,
    period_label: str,
    user_id: str | None = None,
) -> Reading | None:
    q = db.query(Reading).filter(
        Reading.kundli_id == kundli_id,
        Reading.reading_type == reading_type,
        Reading.period_label == period_label,
    )
    if user_id is not None:
        q = q.join(Kundli).filter(Kundli.user_id == user_id)
    return q.order_by(Reading.version.desc(), Reading.generated_at.desc()).first()


def update_reading_feedback(
    db: Session,
    kundli_id: str,
    reading_id: str,
    user_id: str | None,
    rating: int | None,
    feedback: str | None,
) -> Reading | None:
    r = get_reading(db, kundli_id, reading_id, user_id)
    if not r:
        return None
    r.user_rating = rating
    r.user_feedback = feedback
    r.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(r)
    return r


# ── Prediction Claims ─────────────────────────────────────────────────────────

def replace_prediction_claims(
    db: Session,
    reading_id: str,
    claims: list[dict],
    user_id: str | None = None,
) -> list[PredictionClaim]:
    if user_id is not None:
        reading = (
            db.query(Reading)
            .join(Kundli)
            .filter(Reading.id == reading_id, Kundli.user_id == user_id)
            .first()
        )
        if not reading:
            return []
    q = db.query(PredictionClaim).filter(PredictionClaim.reading_id == reading_id)
    if user_id is not None:
        q = q.filter(PredictionClaim.user_id == user_id)
    q.delete()
    rows = [PredictionClaim(**claim) for claim in claims]
    for row in rows:
        db.add(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def get_prediction_claims(
    db: Session,
    kundli_id: str,
    user_id: str,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 200,
) -> list[PredictionClaim]:
    q = db.query(PredictionClaim).filter(
        PredictionClaim.kundli_id == kundli_id,
        PredictionClaim.user_id == user_id,
    )
    if status:
        q = q.filter(PredictionClaim.status == status)
    if start_date:
        q = q.filter(PredictionClaim.target_end_date >= start_date)
    if end_date:
        q = q.filter(PredictionClaim.target_start_date <= end_date)
    return (
        q.order_by(
            PredictionClaim.target_start_date.desc(),
            PredictionClaim.created_at.desc(),
        )
        .limit(limit)
        .all()
    )


def get_prediction_claim(
    db: Session,
    kundli_id: str,
    claim_id: str,
    user_id: str,
) -> PredictionClaim | None:
    return (
        db.query(PredictionClaim)
        .filter(
            PredictionClaim.kundli_id == kundli_id,
            PredictionClaim.id == claim_id,
            PredictionClaim.user_id == user_id,
        )
        .first()
    )


def update_prediction_claim_feedback(
    db: Session,
    kundli_id: str,
    claim_id: str,
    user_id: str,
    status: str,
    feedback: str | None,
) -> PredictionClaim | None:
    claim = get_prediction_claim(db, kundli_id, claim_id, user_id)
    if not claim:
        return None
    claim.status = status
    claim.user_feedback = feedback
    claim.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(claim)
    return claim


# ── User Settings ─────────────────────────────────────────────────────────────

def get_user_settings(db: Session, user_id: str) -> UserSettings | None:
    return db.query(UserSettings).filter(UserSettings.user_id == user_id).first()


def upsert_user_settings(db: Session, user_id: str, data: dict) -> UserSettings:
    settings = get_user_settings(db, user_id)
    if not settings:
        settings = UserSettings(user_id=user_id)
        db.add(settings)
    for key, value in data.items():
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return settings
