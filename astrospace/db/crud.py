from sqlalchemy.orm import Session
from .models import Kundli, Reading


# ── Kundli ────────────────────────────────────────────────────────────────────

def create_kundli(db: Session, data: dict) -> Kundli:
    k = Kundli(**data)
    db.add(k)
    db.commit()
    db.refresh(k)
    return k


def get_kundli(db: Session, kundli_id: str) -> Kundli | None:
    return db.query(Kundli).filter(Kundli.id == kundli_id).first()


def list_kundlis(db: Session) -> list[Kundli]:
    return db.query(Kundli).order_by(Kundli.name).all()


def update_kundli(db: Session, kundli_id: str, data: dict) -> Kundli | None:
    k = get_kundli(db, kundli_id)
    if not k:
        return None
    for key, val in data.items():
        setattr(k, key, val)
    db.commit()
    db.refresh(k)
    return k


def delete_kundli(db: Session, kundli_id: str) -> bool:
    k = get_kundli(db, kundli_id)
    if not k:
        return False
    db.delete(k)
    db.commit()
    return True


# ── Reading ───────────────────────────────────────────────────────────────────

def save_reading(db: Session, kundli_id: str, reading_type: str,
                 content: str, period_label: str = None) -> Reading:
    r = Reading(kundli_id=kundli_id, reading_type=reading_type,
                content=content, period_label=period_label)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def get_readings(db: Session, kundli_id: str, reading_type: str = None) -> list[Reading]:
    q = db.query(Reading).filter(Reading.kundli_id == kundli_id)
    if reading_type:
        q = q.filter(Reading.reading_type == reading_type)
    return q.order_by(Reading.generated_at.desc()).limit(20).all()


def get_latest_reading(db: Session, kundli_id: str, reading_type: str) -> Reading | None:
    return (db.query(Reading)
            .filter(Reading.kundli_id == kundli_id, Reading.reading_type == reading_type)
            .order_by(Reading.generated_at.desc())
            .first())
