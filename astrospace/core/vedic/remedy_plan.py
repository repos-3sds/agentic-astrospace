"""Personal remedy plan — two or three remedies chosen for one chart.

``remedies.recommend()`` lists every affliction it can find, each with five
practices. That is a catalogue, not advice. This module picks at most three
mantra practices, each for a stated reason:

1. **This period** — the remedy Brihat Parashara Hora Shastra (Santhanam tr.,
   ch.52-60) names for the running mahadasha/antardasha pair. When BPHS names
   only charity or a priest-led rite, the antardasha lord's own mantra is used.
2. **Your main life area** — the house the dasha lords occupy and rule most
   strongly, mapped to the deity traditionally prayed to for that part of life.
   The house-to-deity pairing is popular convention, and it is labelled so.
3. **One flag**, only if one is actually present: gandanta, grahan, or the
   antardasha/mahadasha lord debilitated or combust. A flag, not a verdict.

The texts come from ``mantra_corpus/mantras.json`` (built by
``scripts/mantra_corpus/build_corpus.py``), so every practice ships its text
in Telugu script, English letters and Devanagari, with its source.

Non-negotiables enforced here (design_principles.md §4, §6):

* BPHS frames many dasha remedies against disease or early death. That framing
  is never surfaced; only the practice and a page citation are.
* Long recitations (Vishnu Sahasranama, Rudram, Saptashati, Aditya Hridayam)
  are named as the fuller practice, while the counted practice is a short
  verse from the same tradition, so nothing here needs a priest or money.
* Bija and Vedic mantras are not chosen by default: many traditions expect a
  teacher for them. Santana Gopala is never auto-surfaced.
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path

from .constants import SIGN_LORDS
from .doshas import dosha_summary
from .positions import sign_index
from .remedies import GRAHA_REMEDIES, GRAHA_THEME, SAFETY_NOTE, DOSHA_SAFETY_NOTE
from .strength import all_dignities, combustion_status

_CORPUS_DIR = Path(__file__).with_name("mantra_corpus")

MAX_REMEDIES = 3

PLAN_TRADITION_SOURCE = (
    "Brihat Parashara Hora Shastra (R. Santhanam tr.) and common household practice"
)

# Long or teacher-guided texts swapped for a short counted verse from the same
# tradition. The long text is still named, as the fuller practice.
_SHORT_FORM = {
    "sri-rudram": "shiva-panchakshari",
    "shiva-sahasranama": "shiva-panchakshari",
    "vishnu-sahasranama": "rama-nama-sahasranama-tulya",
    "durga-saptashati": "durga-sarvamangala",
    "aditya-hridayam": "surya-dvadasha-nama",
    "durga-navarna": "durga-sarvamangala",
}

# Never chosen automatically (see corpus README, "App care").
_NEVER_AUTO = {"santana-gopala"}

# House → life area. Labels describe a part of life, never an outcome, and no
# area is called "health" (no medical framing). Deity pairings are popular
# household convention, not BPHS.
_LIFE_AREAS: dict[int, dict] = {
    1: {"domain": "self", "label": "Confidence and direction", "mantra": "surya-dvadasha-nama"},
    2: {"domain": "money", "label": "Money and family resources", "mantra": "lakshmi-nama"},
    3: {"domain": "effort", "label": "Courage and effort", "mantra": "hanuman-manojavam"},
    4: {"domain": "home", "label": "Home and family", "mantra": "durga-sarvamangala"},
    5: {"domain": "learning", "label": "Learning and creativity", "mantra": "saraswati-nama"},
    6: {"domain": "effort", "label": "Daily work and routines", "mantra": "hanuman-manojavam"},
    7: {"domain": "relationships", "label": "Partnerships and marriage", "mantra": "durga-sarvamangala"},
    8: {"domain": "inner", "label": "Inner steadiness", "mantra": "shiva-panchakshari"},
    9: {"domain": "dharma", "label": "Faith and guidance", "mantra": "vishnu-dvadashakshari"},
    10: {"domain": "career", "label": "Career and standing", "mantra": "ganesha-nama"},
    11: {"domain": "money", "label": "Income and goals", "mantra": "lakshmi-nama"},
    12: {"domain": "inner", "label": "Rest and letting go", "mantra": "shiva-panchakshari"},
}

# Tie-break when two houses score the same: the more commonly asked-about
# areas first.
_HOUSE_ORDER = [10, 7, 2, 11, 4, 5, 1, 9, 3, 6, 8, 12]

# Weights: the antardasha is what is live now, so it counts more than the
# mahadasha, and occupying a house counts more than ruling it.
_WEIGHTS = {("antardasha", "occupies"): 3, ("antardasha", "rules"): 2,
            ("mahadasha", "occupies"): 2, ("mahadasha", "rules"): 1}

# User-facing framing for texts whose classical framing must not be shown.
_PRESENTATION = {
    "mahamrityunjaya": "A prayer to Shiva for steadiness and well-being.",
    "lakshmi-nama": "Offered as a prayer of gratitude.",
    "hanuman-manojavam": "Praying to Hanuman for courage is popular practice, not a BPHS rule.",
}

_FLAG_MANTRA = {"gandanta": "ganesha-nama", "grahan": "durga-sarvamangala"}


@lru_cache(maxsize=1)
def corpus() -> dict[str, dict]:
    """Mantra entries keyed by id."""
    data = json.loads((_CORPUS_DIR / "mantras.json").read_text(encoding="utf-8"))
    return {m["id"]: m for m in data["mantras"]}


@lru_cache(maxsize=1)
def recordings() -> dict[str, dict]:
    """Recited audio per mantra id, from mantra_corpus/mantra_audio.json.

    The files are served from the public site (firebase-public/audio/), not
    the API, so they cache at the edge and play without a sign-in. A mantra
    with no entry keeps audio_url null and the app falls back to reading the
    text aloud.
    """
    path = _CORPUS_DIR / "mantra_audio.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _audio_base() -> str:
    return os.getenv("ASTROSPACE_PUBLIC_AUDIO_BASE", "https://asksiddha.app/audio").rstrip("/")


@lru_cache(maxsize=1)
def bphs_antardasha() -> dict[tuple[str, str], dict]:
    """BPHS dasha/bhukti remedy rows keyed by (mahadasha, antardasha)."""
    data = json.loads((_CORPUS_DIR / "bphs_antardasha.json").read_text(encoding="utf-8"))
    return {(r["mahadasha"], r["antardasha"]): r for r in data["rows"]}


def _public_citation(cite: str | None) -> str | None:
    """A book citation without the private knowledge-base file path."""
    return re.sub(r"\s*\(KB:[^)]*\)", "", cite) if cite else None


def _counted(mantra_id: str) -> str | None:
    """The short, open mantra to count for a corpus id, or None."""
    entry = corpus().get(_SHORT_FORM.get(mantra_id, mantra_id))
    if not entry or entry["id"] in _NEVER_AUTO:
        return None
    if not entry.get("text") or entry["tier"] != "simple":
        return None
    return entry["id"]


def _practice(mantra_id: str, planet: str | None, applies_to: dict,
              fuller: str | None = None) -> dict:
    m = corpus()[mantra_id]
    count = m.get("practical_count") or 108
    # A graha's own mantra keeps the graha's weekday; a deity mantra keeps
    # only a day the corpus records for it.
    day = m.get("preferred_day") or (
        GRAHA_REMEDIES[planet]["day"] if planet and m["category"].startswith("graha_") else None)
    verb = "Chant" if count >= 108 else "Recite"
    when = f", ideally on {day} morning" if day else ", at a quiet time each day"
    fuller_entry = corpus().get(fuller) if fuller and fuller != mantra_id else None
    observance = _PRESENTATION.get(mantra_id)
    return {
        "practice_slug": mantra_id,
        "mantra_id": mantra_id,
        "type": "mantra",
        "title": m["name"],
        "instructions": f"{verb} {count} times{when}.",
        "cadence": "daily" if not day else "weekly",
        "target_count": count,
        "preferred_day": day,
        "optional_cost": False,
        "planet": planet,
        "deity": m.get("deity"),
        "applies_to": applies_to,
        "tradition_source": m["source_citation"],
        "kb_citation": _public_citation(m.get("kb_citation")),
        "is_convention_dependent": m["confidence"] in ("popular_tradition", "tradition_attributed", "sources_disagree"),
        "observance_note": observance,
        "confidence": m["confidence"],
        "text": m["text"],
        "meaning": {"en": m.get("meaning_en"), "te": m.get("meaning_te"), "hi": m.get("meaning_hi")},
        "count_note": m.get("count_note"),
        "fuller_practice": (
            {"mantra_id": fuller_entry["id"], "name": fuller_entry["name"],
             "note": fuller_entry.get("count_note")}
            if fuller_entry else None
        ),
        "audio": _audio_block(m, count),
    }


def _audio_block(m: dict, count: int) -> dict:
    block = {
        "text": m["text"]["en"],
        "transliteration": m["text"]["iast"],
        "language": "sa",
        "count_target": count,
        "loop_seconds": (m.get("audio") or {}).get("est_seconds_per_repetition"),
        "audio_url": None,
        "source_status": "pending_assets",
        "note": "Text is final; recorded audio is a pending content task.",
    }
    rec = recordings().get(m["id"])
    if rec:
        block.update({
            "audio_url": f"{_audio_base()}/{rec['file']}",
            # Synthesised recitation, not a trained reciter: say so.
            "source_status": "tts_recitation",
            "note": "Recited by a synthetic voice over a soft veena and tanpura background.",
            "voice_start": rec.get("voice_start"),
            "voice_seconds": rec.get("voice_seconds"),
            "lines": rec.get("lines") or [],
        })
    return block


def _houses(positions: dict, lagna_lon: float, planet: str) -> dict[str, list[int]]:
    lagna = sign_index(lagna_lon)
    occupied = []
    if planet in positions:
        occupied = [(sign_index(positions[planet]["lon"]) - lagna) % 12 + 1]
    ruled = [h for h in range(1, 13) if SIGN_LORDS[(lagna + h - 1) % 12] == planet]
    return {"occupies": occupied, "rules": ruled}


def main_life_area(positions: dict, lagna_lon: float, md: str | None,
                   ad: str | None) -> list[dict]:
    """Houses ranked by how strongly the running dasha lords point at them."""
    scores: dict[int, int] = {}
    why: dict[int, list[str]] = {}
    for level, lord in (("antardasha", ad), ("mahadasha", md)):
        if not lord:
            continue
        for rel, houses in _houses(positions, lagna_lon, lord).items():
            for h in houses:
                scores[h] = scores.get(h, 0) + _WEIGHTS[(level, rel)]
                why.setdefault(h, []).append(f"{lord} ({level}) {rel} house {h}")
    ranked = sorted(scores, key=lambda h: (-scores[h], _HOUSE_ORDER.index(h)))
    return [{"house": h, "score": scores[h], "evidence": why[h], **_LIFE_AREAS[h]} for h in ranked]


def _flag(positions: dict, lagna_lon: float, md: str | None, ad: str | None) -> dict | None:
    doshas = dosha_summary(positions, lagna_lon)
    for name in ("gandanta", "grahan"):
        d = doshas.get(name) or {}
        if d.get("active"):
            return {"recommendation_id": f"dosha-{name}", "kind": "dosha", "dosha": name,
                    "planet": "Ketu" if name == "gandanta" else "Rahu",
                    "mantra": _FLAG_MANTRA[name],
                    "reason_short": ("A gandanta (junction) placement is in your chart"
                                     if name == "gandanta" else
                                     "A grahan (eclipse) combination is in your chart"),
                    "source_status": d.get("source_status", "convention_dependent")}
    dignities = all_dignities(positions)
    for lord in (ad, md):
        if not lord or lord not in positions:
            continue
        if (dignities.get(lord) or {}).get("dignity") == "Debilitated":
            return {"recommendation_id": f"dignity-debilitated-{lord.lower()}", "kind": "dignity",
                    "planet": lord, "mantra": f"{lord.lower()}-stotra",
                    "reason_short": f"{lord}, which runs your period now, is debilitated",
                    "source_status": "verified_common"}
        if lord not in ("Sun", "Rahu", "Ketu") and (combustion_status(lord, positions) or {}).get("active"):
            return {"recommendation_id": f"combustion-{lord.lower()}", "kind": "combustion",
                    "planet": lord, "mantra": f"{lord.lower()}-stotra",
                    "reason_short": f"{lord}, which runs your period now, is close to the Sun",
                    "source_status": "convention_dependent"}
    return None


def remedy_plan(positions: dict, lagna_lon: float, dasha: dict | None) -> dict:
    """At most three remedies for this chart, most important first."""
    current = (dasha or {}).get("current") or {}
    md_period = current.get("mahadasha") or {}
    ad_period = current.get("antardasha") or {}
    md, ad = md_period.get("lord"), ad_period.get("lord")
    md = md if md in GRAHA_REMEDIES else None
    ad = ad if ad in GRAHA_REMEDIES else None

    groups: list[dict] = []
    used: set[str] = set()

    def add(group: dict) -> None:
        group["priority"] = len(groups) + 1
        groups.append(group)
        used.add(group["practices"][0]["mantra_id"])

    # 1. This period.
    if md and ad:
        row = bphs_antardasha().get((md, ad)) or {}
        chosen, fuller = None, None
        for mid in row.get("mantra_ids") or []:
            chosen = _counted(mid)
            if chosen:
                fuller = mid if mid != chosen and not corpus()[mid].get("text") else None
                break
        from_bphs = chosen is not None
        if not chosen:
            chosen = f"{ad.lower()}-nama"
        add({
            "recommendation_id": f"plan-period-{md.lower()}-{ad.lower()}",
            "slot": "period",
            "trigger": {"kind": "dasha", "planet": ad, "level": "antardasha", "mahadasha": md},
            "reason_short": f"For your {md}–{ad} period",
            "reason_practitioner": (
                f"{md} mahadasha, {ad} antardasha ({ad_period.get('start')} to "
                f"{ad_period.get('end')}). "
                + ("BPHS names this practice for the pair." if from_bphs else
                   "BPHS names only charity or a priest-led rite for this pair, so "
                   f"the {ad} mantra is used.")
            ),
            "theme": GRAHA_THEME[ad],
            "evidence": {"mahadasha": md, "antardasha": ad,
                         "start": ad_period.get("start"), "end": ad_period.get("end"),
                         "kb_citation": _public_citation(row.get("kb_citation"))},
            "source_status": "verified_common" if from_bphs else "convention_dependent",
            "tradition_source": _public_citation(row.get("kb_citation")) or PLAN_TRADITION_SOURCE,
            "convention_dependent": not from_bphs,
            "observance_note": (
                None if from_bphs else
                "BPHS gives no recitation for this period; using the sub-period "
                "lord's own mantra is common practice."
            ),
            "safety_note": SAFETY_NOTE,
            "practices": [_practice(chosen, ad, {"kind": "dasha", "planet": ad}, fuller)],
        })

    # 2. Main life area.
    for area in main_life_area(positions, lagna_lon, md, ad):
        if area["mantra"] in used:
            continue
        add({
            "recommendation_id": f"plan-area-{area['domain']}",
            "slot": "life_area",
            "domain": area["domain"],
            "domain_label": area["label"],
            "house": area["house"],
            "trigger": {"kind": "life_area", "house": area["house"], "domain": area["domain"]},
            "reason_short": f"For {area['label'].lower()}, the area your period points at",
            "reason_practitioner": "; ".join(area["evidence"]) + " (whole-sign houses).",
            "evidence": {"house": area["house"], "score": area["score"], "basis": area["evidence"]},
            "source_status": "convention_dependent",
            "tradition_source": PLAN_TRADITION_SOURCE,
            "convention_dependent": True,
            "observance_note": (
                "Which deity is prayed to for which part of life is household "
                "convention and varies by family and region."
            ),
            "safety_note": SAFETY_NOTE,
            "practices": [_practice(area["mantra"], None, {"kind": "life_area", "house": area["house"]})],
        })
        break

    # 3. One flag, only if present.
    flag = _flag(positions, lagna_lon, md, ad)
    if flag and flag["mantra"] not in used and len(groups) < MAX_REMEDIES:
        trigger = {k: flag[k] for k in ("kind", "planet", "dosha") if k in flag}
        add({
            "recommendation_id": flag["recommendation_id"],
            "slot": "flag",
            "trigger": trigger,
            "reason_short": flag["reason_short"],
            "reason_practitioner": flag["reason_short"] + ". This is a flag, not a verdict.",
            "framing": "This is a flag, not a verdict.",
            "evidence": trigger,
            "source_status": flag["source_status"],
            "tradition_source": PLAN_TRADITION_SOURCE,
            "convention_dependent": True,
            "observance_note": "Classical texts prescribe no single mantra for this; this is common practice.",
            "safety_note": DOSHA_SAFETY_NOTE,
            "practices": [_practice(flag["mantra"], flag["planet"], trigger)],
        })

    return {
        "groups": groups[:MAX_REMEDIES],
        "count": min(len(groups), MAX_REMEDIES),
        "period": {"mahadasha": md, "antardasha": ad,
                   "start": ad_period.get("start"), "end": ad_period.get("end")},
        "note": None if groups else "Nothing in your chart is asking for a remedy right now.",
        "disclaimer": SAFETY_NOTE,
    }
