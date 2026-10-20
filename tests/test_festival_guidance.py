"""The festival sheet's to-dos and mantra names (festival_guidance.py).

Hawk (2026-10-20): grounded, simple and accurate, not overwhelming. These tests
hold the shape to that, and keep the copy inside the product's rules.
"""
import json
import re
from pathlib import Path

import pytest

from astrospace.core.vedic import festival_guidance as G
from astrospace.core.vedic import festivals as F

CORPUS = json.loads(
    (Path(F.__file__).parent / "mantra_corpus" / "mantras.json").read_text()
)["mantras"]
CORPUS_BY_ID = {m["id"]: m for m in CORPUS}

ALL = [*G.FESTIVAL_GUIDANCE.items(), *G.VRAT_GUIDANCE.items()]

# Words that sell fear or outcomes, or push spending.
BANNED = re.compile(
    r"\b(must|never miss|guarantee\w*|dosha|remove\w*|wealth|prosperity|"
    r"bad luck|curse\w*|evil eye|cosmic|book a|pay for)\b", re.I)
# Bija and Vedic mantras want a teacher; Santana Gopala is never auto-surfaced
# (docs/mantra_corpus.md, care rules).
NOT_BY_DEFAULT = re.compile(r"-(bija|vedic|vedic-taittiriya)$|^santana-gopala$|^durga-navarna$")


def test_every_festival_has_guidance_and_nothing_is_orphaned():
    slugs = {f["slug"] for f in F.FESTIVALS}
    assert set(G.FESTIVAL_GUIDANCE) == slugs
    assert set(G.VRAT_GUIDANCE) == set(F.VRAT_NAMES)


@pytest.mark.parametrize("key,entry", ALL, ids=[k for k, _ in ALL])
def test_entries_stay_small(key, entry):
    assert 2 <= len(entry["todo"]) <= 4
    assert len(entry["mantras"]) <= 2
    assert entry["how"]
    for line in [*entry["todo"], entry["how"]]:
        assert len(line) <= 120, line
        assert line.strip() == line and line[-1] in ".)", line


@pytest.mark.parametrize("key,entry", ALL, ids=[k for k, _ in ALL])
def test_copy_keeps_the_product_rules(key, entry):
    text = " ".join([*entry["todo"], entry["how"], *(n for n, _ in entry["mantras"])])
    assert not BANNED.search(text), BANNED.search(text).group(0)


@pytest.mark.parametrize("key,entry", ALL, ids=[k for k, _ in ALL])
def test_fasts_carry_the_health_caveat(key, entry):
    text = " ".join(entry["todo"] + [entry["how"]]).lower()
    if re.search(r"\bfast", text):
        assert "health" in text, key


@pytest.mark.parametrize("key,entry", ALL, ids=[k for k, _ in ALL])
def test_corpus_links_are_real_and_safe(key, entry):
    for name, corpus_id in entry["mantras"]:
        if corpus_id is None:
            continue
        assert corpus_id in CORPUS_BY_ID, corpus_id
        assert not NOT_BY_DEFAULT.search(corpus_id), corpus_id


def test_snake_days_say_not_to_feed_live_snakes():
    for slug in ("nag_panchami", "nagula_chavithi"):
        assert any("live snake" in t for t in G.FESTIVAL_GUIDANCE[slug]["todo"])


def test_gold_is_never_pushed():
    for slug in ("akshaya_tritiya", "dhanteras"):
        text = " ".join(G.FESTIVAL_GUIDANCE[slug]["todo"]).lower()
        assert "not needed" in text or "not a need" in text


def test_occurrences_and_vrat_rows_carry_guidance():
    rows = F.occurrences(2026, city="Chennai", nation="IN", slugs=["diwali"])
    assert rows and rows[0]["guidance"]["todo"]
    assert rows[0]["guidance"]["mantras"][0] == {
        "name": "Om Shreem Mahalakshmyai Namah", "corpus_id": "lakshmi-nama"}
    assert G.for_vrat("pradosham")["mantras"][0]["corpus_id"] == "shiva-panchakshari"
    assert G.for_festival("no-such-slug") == {"todo": [], "how": None, "mantras": []}


def test_gangaur_is_not_called_gowri_habba():
    """Chaitra Shukla Tritiya is Gangaur; Gowri Habba is the day before
    Ganesh Chaturthi, which is Hartalika Teej's day."""
    assert "Gowri" not in F.FESTIVALS_BY_SLUG["gauri_habba"]["name"]
    assert "Gowri Habba" in F.FESTIVALS_BY_SLUG["hartalika_teej"]["name"]
