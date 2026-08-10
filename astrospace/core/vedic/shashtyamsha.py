"""Shashtyamsha (D-60) deity layer — the 60 named deities ruling each 0.5-degree
division of a sign, and the benefic/malefic (Saumya/Krura) nature of each.

vargas.d60() already computes the D-60 *sign* correctly; this module adds
the deity name on top of that, using the same division index.

Provenance (2026-08-10): an earlier attempt at this module was built then
deliberately deleted mid-session and NOT shipped, because its 60-name list
traced back to the same AI-extraction pipeline that produced this session's
other fabricated tables (a wrong Vimshopaka weight table, a wrong Jaimini
karaka scheme, self-contradicting Shayanadi Avastha worked examples) — only
the odd/even reversal *arithmetic* had been checked, never the 60 names
themselves against an independent source.

This version instead cross-checked three independently-fetched web sources
against each other, name by name:
  - https://www.rahasyavedicastrology.com/d60-shastiamsa-devata/
  - https://www.shivohampath.com/post/d60-shashtiamsha-past-life-karma-at-full-resolution
  - https://www.sarvatobhadra.com/amsha-rulers-shashtiamsha-d60/ (excluded — see below)

The first two agree on all 60 names in order; the handful of surface
mismatches between them (division 10 "Vahni"/"Agni", division 48
"Karaladamshtra"/"Drastakaral", division 51 "Kalagni"/"Kalapavaka") turned
out, on the second source, to be the *same* pair of accepted Sanskrit
synonyms given side by side (both mean "fire", "terrible-fanged", etc.) —
not a disagreement. shivohampath.com's inline benefic/malefic tag for each
deity was additionally sanity-checked against the literal meaning of the
Sanskrit name (e.g. "Kroora" literally means "cruel" -> malefic;
"Poornachandra" literally means "full moon" -> benefic) and holds up.

sarvatobhadra.com was fetched as a third opinion and excluded: its names
diverge sharply from division ~48 onward with what looks like an index
shift, and several of its benefic/malefic tags contradict the literal
Sanskrit meaning of the name (e.g. it calls Poornachandra malefic) — the
same OCR/row-misalignment failure signature already seen and rejected
elsewhere in this project's validation pass (see
tests/test_bphs_ground_truth.py's Vimshopaka Bala provenance note).

Still flagged source_status: convention_dependent — no primary BPHS verse
was located in this pass, only secondary-source agreement.

Reversal rule (per both retained sources): division 1..60 map to deities
1..60 directly in odd signs (Aries, Gemini, Leo, Libra, Sagittarius,
Aquarius); in even signs the same 60 names apply in reverse order (the
sign's first division gets deity 60, its last division gets deity 1).
"""
# 1-indexed conceptually; DEITIES[i] is deity (i+1). (name, "benefic"|"malefic")
DEITIES: list[tuple[str, str]] = [
    ("Ghora", "malefic"), ("Rakshasa", "malefic"), ("Deva", "benefic"),
    ("Kubera", "benefic"), ("Yaksha", "benefic"), ("Kinnara", "benefic"),
    ("Bhrashta", "malefic"), ("Kulaghna", "malefic"), ("Garala", "malefic"),
    ("Vahni", "malefic"), ("Maya", "malefic"), ("Purishaka", "malefic"),
    ("Apampathi", "benefic"), ("Marut", "benefic"), ("Kaala", "malefic"),
    ("Sarpa", "malefic"), ("Amrita", "benefic"), ("Indu", "benefic"),
    ("Mridu", "benefic"), ("Komala", "benefic"), ("Heramba", "benefic"),
    ("Brahma", "benefic"), ("Vishnu", "benefic"), ("Maheswara", "benefic"),
    ("Deva", "benefic"), ("Ardra", "benefic"), ("Kalinasa", "benefic"),
    ("Kshiteesa", "benefic"), ("Kamalakara", "benefic"), ("Gulika", "malefic"),
    ("Mrityu", "malefic"), ("Kaala", "malefic"), ("Davagni", "malefic"),
    ("Ghora", "malefic"), ("Yama", "malefic"), ("Kantaka", "malefic"),
    ("Sudha", "benefic"), ("Amrita", "benefic"), ("Poornachandra", "benefic"),
    ("Vishadagdha", "malefic"), ("Kulanasa", "malefic"), ("Vamsakshaya", "malefic"),
    ("Utpata", "malefic"), ("Kaala", "malefic"), ("Saumya", "benefic"),
    ("Komala", "benefic"), ("Seetala", "benefic"), ("Karaladamshtra", "malefic"),
    ("Chandramukhi", "benefic"), ("Praveena", "benefic"), ("Kalagni", "malefic"),
    ("Dandayudha", "malefic"), ("Nirmala", "benefic"), ("Saumya", "benefic"),
    ("Kroora", "malefic"), ("Atiseetala", "benefic"), ("Amrita", "benefic"),
    ("Payodhi", "benefic"), ("Bhramana", "malefic"), ("Chandrarekha", "benefic"),
]
assert len(DEITIES) == 60


def _division(lon: float) -> tuple[int, int]:
    """(sign index 0..11, division m 0..59) within the sign for a longitude.
    Mirrors vargas.d60()'s own division math exactly."""
    lon = lon % 360.0
    s = int(lon // 30)
    d = lon % 30.0
    m = min(int(d * 2), 59)
    return s, m


def d60_deity(lon: float) -> dict:
    """D-60 deity for a sidereal longitude.

    Odd signs (s % 2 == 0, i.e. Aries/Gemini/Leo/Libra/Sagittarius/Aquarius)
    read the 60 deities in direct order; even signs read them reversed.
    """
    s, m = _division(lon)
    deity_number = (m + 1) if s % 2 == 0 else (60 - m)
    name, nature = DEITIES[deity_number - 1]
    return {
        "deity": name,
        "number": deity_number,
        "nature": nature,
        "source_status": "convention_dependent",
        "rule": (
            "Odd signs read the 60 deities 1-60 in direct order; even signs "
            "read the same 60 in reverse. Cross-checked against two "
            "independent secondary sources agreeing on all 60 names; no "
            "primary BPHS verse located."
        ),
    }
