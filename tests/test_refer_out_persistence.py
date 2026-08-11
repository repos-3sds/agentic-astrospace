"""Every safety refer-out kind must survive the round trip to storage.

ASK-001 was a P0: the deployed Postgres CHECK on `ask_messages.refer_out_kind`
allowed ('medical','legal','financial','longevity','emergency') while the
application had always emitted ('death','health','legal','money'). Only 'legal'
overlapped, so three of the four categories raised CheckViolation on insert,
`_safe_stream` turned that into a `fatal_error` frame, and a reader asking
"Will I die this year?" got "Something went wrong while generating this answer."
instead of the referral. The guardrail fired and its delivery failed.

It survived a green suite because the mismatch lived only in SQL that no test
executed: the model declared a bare String, and the tests run on in-memory
SQLite. So the lesson is not "add a case for death" — it is that the three
places naming these categories had no mechanism forcing them to agree. These
tests are that mechanism, and they are deliberately written to run anywhere
rather than requiring a live Postgres, because a check that only runs against
a real database is a check that will not run.

Three sources of truth, pinned against each other:
  1. `safety.REFER_OUT_ANSWERS`         — what the application emits
  2. the model's CheckConstraint        — what the ORM/test DB accepts
  3. the newest migration's CHECK       — what deployed Postgres accepts
"""
import re
from pathlib import Path

import pytest

from astrospace.agents.safety import REFER_OUT_ANSWERS, refer_out_kind
from astrospace.db.models import AskMessage

MIGRATIONS = Path(__file__).resolve().parents[1] / "supabase" / "migrations"
CANONICAL = {"death", "health", "legal", "money"}


def _allowed_in_sql() -> set[str]:
    """The refer_out_kind values deployed Postgres will accept.

    Reads the *latest* migration that touches the constraint, so this keeps
    telling the truth as further migrations are added rather than pinning one
    filename forever.
    """
    touching = sorted(
        p for p in MIGRATIONS.glob("*.sql")
        if "refer_out_kind" in p.read_text()
    )
    assert touching, "no migration defines refer_out_kind"
    text = touching[-1].read_text()
    match = re.findall(
        r"check\s*\(\s*refer_out_kind\s+in\s*\(([^)]*)\)", text, re.IGNORECASE
    )
    assert match, f"no refer_out_kind CHECK found in {touching[-1].name}"
    return {v.strip().strip("'\"") for v in match[-1].split(",") if v.strip()}


def _allowed_in_model() -> set[str]:
    for constraint in AskMessage.__table__.constraints:
        text = str(getattr(constraint, "sqltext", ""))
        if "refer_out_kind" in text:
            inner = re.findall(r"IN\s*\(([^)]*)\)", text, re.IGNORECASE)
            if inner:
                return {v.strip().strip("'\"") for v in inner[-1].split(",") if v.strip()}
    raise AssertionError("AskMessage has no refer_out_kind CheckConstraint")


def test_application_emits_exactly_the_canonical_kinds():
    """If a category is added to safety.py, the two checks below force the
    model and the migration to be updated in the same change."""
    assert set(REFER_OUT_ANSWERS) == CANONICAL


def test_deployed_constraint_accepts_every_kind_the_app_emits():
    """The exact assertion that was missing when ASK-001 shipped."""
    missing = set(REFER_OUT_ANSWERS) - _allowed_in_sql()
    assert not missing, (
        f"safety.py emits {sorted(missing)} but the migration's CHECK rejects "
        f"them — inserting one raises CheckViolation and the reader sees a "
        f"generation error instead of the safety referral"
    )


def test_model_constraint_accepts_every_kind_the_app_emits():
    missing = set(REFER_OUT_ANSWERS) - _allowed_in_model()
    assert not missing, f"model CheckConstraint rejects {sorted(missing)}"


def test_model_and_migration_agree_with_each_other():
    """Guards the reverse drift: a migration widened without the model, which
    would let a value persist in production that the tests never accept."""
    assert _allowed_in_model() == _allowed_in_sql()


def test_retired_vocabulary_is_gone():
    """The pre-fix values must not linger in the constraint — leaving both
    vocabularies permitted would hide exactly this bug next time."""
    assert not ({"medical", "financial", "longevity"} & _allowed_in_sql())


@pytest.mark.parametrize("question,expected", [
    ("Will I die this year?", "death"),
    ("How long will I live?", "death"),
    ("Do I have cancer?", "health"),
    ("Should I stop my medication?", "health"),
    ("Will I win my court case?", "legal"),
    ("Should I buy TCS stock right now?", "money"),
])
def test_each_refer_out_route_produces_a_persistable_kind(question, expected):
    """Walks the real gate rather than asserting on the table directly: the
    kinds must be reachable from actual questions, not merely declared."""
    kind = refer_out_kind(question)
    assert kind == expected
    assert kind in _allowed_in_sql()
    assert kind in _allowed_in_model()
