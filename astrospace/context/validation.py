"""Where this chart is genuinely ambiguous — the engine's half of the
validation loop.

A real astrologer validates before predicting: they ask about the past, and
what the answer rules out is what makes the next hour worth paying for. The
naive version of that in software is a cold-reading machine — ask "have you had
money trouble?", hear "yes", reply "yes, your chart shows that". The agent
learned nothing and the reader was handed their own disclosure back as insight.

Two things stop that, and this module is the first. The second is ordering (the
agent commits to a falsifiable claim, with a confidence, BEFORE it sees the
answer — see `agents/validation_agent.py` and the probe store).

The first is *which question gets asked*. Rapport questions are worthless here.
A question earns its place only when the chart genuinely supports more than one
reading and the answer tells them apart. That is a property of the chart, not
of the conversation, so the engine picks the slots and the model only writes the
question and the option copy. If the model picked slots too, it would ask about
things the chart cannot speak to, and every answer would be unfalsifiable.

What "more than one defensible reading" means concretely here: a planet gives
the results of the houses it RULES and of the house it OCCUPIES (BPHS, and
about as uncontroversial as this subject gets). When those two point at
different areas of a reader's financial life, both readings are classically
defensible and only the reader knows which actually happened. That divergence
is the ambiguity — it is not a heuristic about how "interesting" a placement
looks.

Wealth only, deliberately. The handoff's instruction was to make hit rate
visible on one real domain before generalising, and the slot generators below
are wealth-shaped (the house-sense table is money-sense). `validation_slots()`
returns `[]` for every other domain rather than guessing at one.
"""
from __future__ import annotations

# Each house in its MONEY sense only — this is a projection of the standard
# significations onto one domain, not a general-purpose house table (the 4th is
# far more than property, the 8th far more than inheritance). Restricting it
# this way is what keeps the candidate readings below about the reader's
# finances instead of drifting into whatever else the house covers.
_WEALTH_HOUSE_SENSE: dict[int, str] = {
    1: "own effort and initiative — money that follows from what they personally drive",
    2: "savings and accumulated wealth, family money, what is held rather than earned",
    3: "self-started enterprise, side ventures, short efforts",
    4: "property, land, vehicles, the home itself as an asset",
    5: "speculation, windfalls, investments taken as a position",
    6: "debt, loans and EMIs, service income, competitive/adversarial money",
    7: "business partnership, trade, a spouse's or partner's finances",
    8: "inheritance, other people's money, sudden gain or sudden loss",
    9: "fortune, support from elders or family, long-range or dharmic gain",
    10: "career income, salary, employer and status",
    11: "gains and income, networks, what comes in from outside",
    12: "expenditure and outflow, foreign spending, money locked away",
}

# The escape hatch, on every slot. Without it the reader is forced into one of
# the chart's own guesses and the hit rate this loop exists to measure is
# inflated by construction — a probe that cannot come back "no" is not a test.
_NEITHER = {
    "key": "neither",
    "gloss": "neither pattern describes those years",
}
_SKIP = {
    "key": "skip",
    "gloss": "reader declines to answer — recorded, never scored as a hit or a miss",
}

# Primary wealth houses (taxonomy: 2 and 11). A slot anchored to one of these
# outranks a slot anchored to a secondary house, because a miss on the savings
# or income axis says more about this chart than a miss on, say, the 6th.
_PRIMARY_HOUSES = (2, 11)


# Candidate keys that mean "more than one of the above was true". Kept beside
# the candidate vocabulary itself, not in the persistence layer, because
# `score_answer` below is only correct as long as it and the generators agree
# on these strings — separating them is how they drift apart.
_COMPOUND_ANSWERS = {"both"}


def score_answer(claim_candidate: str, answer_key: str | None) -> str:
    """How a committed claim scored against what the reader actually said.

    Deliberately blunt — confirmed, missed, partial, skipped — because the
    number this loop exists to produce is a hit rate, and a hit rate built on
    generous partial credit measures nothing. A decline is `skipped` and is
    never counted either way: a reader choosing not to answer is not evidence
    about the chart.
    """
    if not answer_key or answer_key == "skip":
        return "skipped"
    if answer_key == claim_candidate:
        return "confirmed"
    if answer_key in _COMPOUND_ANSWERS:
        return "partial"
    return "missed"


def life_context_section(probes: list[dict]) -> dict:
    """The answered probes, shaped for the bundle.

    This is the payoff: the reader told us something the chart could not, and
    every later reading should be built on it rather than re-guessing. Two
    things travel with it deliberately.

    First, only ANSWERED probes appear. An outstanding commitment is not
    context, and putting it in the bundle would hand the model its own
    unresolved prediction to narrate as if it were established.

    Second, `calibration` is included even when it is unflattering. A hit rate
    is the number this whole loop exists to produce, and a model that can see
    it has a reason to hedge a domain it has been getting wrong — which is the
    correct behaviour and the opposite of what a hidden score would produce.
    Skipped probes are excluded from the denominator: a reader declining to
    answer is not evidence about the chart either way.
    """
    answered = [p for p in probes if p.get("status") in
                ("confirmed", "missed", "partial", "skipped")]
    scored = [p for p in answered if p["status"] != "skipped"]
    hits = sum(1 for p in scored if p["status"] == "confirmed")
    partials = sum(1 for p in scored if p["status"] == "partial")
    return {
        "available": bool(answered),
        "reported": [
            {
                "slot_id": p.get("slot_id"),
                "kind": p.get("slot_kind"),
                "window": {"label": p.get("anchor_label"),
                           "start": p.get("anchor_start"),
                           "end": p.get("anchor_end")},
                "question": p.get("question"),
                "answer": p.get("answer_key"),
                "answer_note": p.get("answer_text"),
                "outcome": p.get("status"),
            }
            for p in answered
        ],
        "calibration": {
            "scored": len(scored),
            "confirmed": hits,
            "partial": partials,
            "missed": sum(1 for p in scored if p["status"] == "missed"),
            "skipped": len(answered) - len(scored),
            # Partials count as half — they mean the committed reading was one
            # of several that turned out true, which is neither a hit nor a
            # clean miss.
            "hit_rate": (round((hits + 0.5 * partials) / len(scored), 2)
                         if scored else None),
        },
        "note": (
            "Reader-reported, not chart-derived. These are facts about their "
            "life that the chart could not supply. Treat them as true and "
            "build on them; where a reported answer contradicts a placement, "
            "believe the reader. Never repeat one back to them as though the "
            "chart revealed it — they told you."
        ),
    }


def _ord(house: int | None) -> str:
    """"2nd", not "2th". This text reaches the model, and a bundle that writes
    house numbers wrongly invites an answer that repeats them wrongly."""
    if house is None:
        return "unknown"
    if 11 <= house % 100 <= 13:
        return f"{house}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(house % 10, "th")
    return f"{house}{suffix}"


def _and_list(parts: list[str]) -> str:
    """"the 5th and 12th", not "the 5th, 12th". Same reason as `_ord`."""
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def _house_row(bundle: dict, house: int) -> dict | None:
    for row in bundle.get("houses") or []:
        if row.get("house") == house:
            return row
    return None


def _rules_houses(bundle: dict, planet: str) -> list[int]:
    """Which of THIS DOMAIN's houses the planet rules. The bundle only carries
    the domain's own houses, which is exactly the right scope — a wealth probe
    should not be built on the planet's rulership of the 3rd."""
    return sorted(
        row["house"] for row in bundle.get("houses") or []
        if row.get("lord") == planet
    )


def _candidate(house: int, role: str) -> dict:
    return {
        "key": f"h{house}_{role}",
        "house": house,
        "role": role,
        "gloss": _WEALTH_HOUSE_SENSE[house],
    }


def _divergent_candidates(bundle: dict, planet: str,
                          occupied_house: int | None) -> list[dict]:
    """The two-or-more defensible readings of one planet, or nothing.

    Returns `[]` when rulership and occupation point at the same area — that is
    a planet saying one thing clearly, which is the opposite of a slot worth
    asking about.
    """
    ruled = [h for h in _rules_houses(bundle, planet) if h in _WEALTH_HOUSE_SENSE]
    candidates = [_candidate(h, "ruled") for h in ruled]
    if occupied_house in _WEALTH_HOUSE_SENSE and occupied_house not in ruled:
        candidates.append(_candidate(occupied_house, "occupied"))
    return candidates if len(candidates) >= 2 else []


# A reader cannot validate a period they spent as a small child, and a
# mahadasha can easily be 20 years long — one test chart's Venus mahadasha ran
# from age 2 to age 22. Fourteen is a judgement call, not a sourced number: it
# is roughly where "what were those years like for your family's money" starts
# having an answer the reader owns rather than one they were told.
_MIN_RECALL_AGE = 14
# A twenty-year window is not falsifiable. "Between 2002 and 2022, did your
# money mostly come through X" can be answered "yes, sort of" about almost any
# X, because two decades of anyone's finances contain a bit of everything — and
# a probe that cannot come back cleanly wrong measures nothing, the same defect
# as a missing "neither" option. Ten years is again a judgement call: long
# enough that a mahadasha-scale pattern can show, short enough that the reader
# is characterising a stretch rather than a life.
_MAX_ANCHOR_YEARS = 10
# Below this a window is too short to have a character at all — a two-month
# antardasha is a date, not a period the reader can describe.
_MIN_ANCHOR_YEARS = 0.5
# Beyond this a window is inside the reader's life but outside useful recall.
_MAX_ANCHOR_AGE_YEARS = 15


def _shift_date(date_str: str, years: float) -> str:
    """Date arithmetic on the ISO strings the timeline already carries.

    Deliberately approximate — this shifts an anchor boundary by a number of
    years to keep a question answerable, and being a day or two out on a
    ten-year clamp changes nothing about whether the reader can answer it.
    """
    from datetime import date, timedelta
    try:
        base = date.fromisoformat(date_str[:10])
    except (TypeError, ValueError):
        return date_str
    return (base + timedelta(days=years * 365.2425)).isoformat()


def _anchor_from(entry: dict, as_of_date: str, as_of_age: float | None = None) -> dict | None:
    """The window a question is asked about, or None if nothing askable is left.

    Every generator builds its anchor here, and that is the point. The age
    floor originally lived in `_recallable`, which only `_dasha_boundary_slots`
    called — so two of the three generators happily anchored to the whole
    current mahadasha and 8% of emitted slots still started before age 14, one
    of them at age 3.7. A rule about what makes a window answerable belongs on
    the window, not in one of the three places windows are made.

    Three clamps, all for the same reason — the reader has to be able to answer:

    * the END never runs past today. A mahadasha the reader is currently in
      extends years into the future, and an unclamped anchor asked "between
      2021 and 2041, did your money mostly come through X" — fifteen years of
      which have not happened.
    * the START never precedes age 14, so no question reaches into a childhood
      the reader can only report second-hand.
    * the SPAN never exceeds `_MAX_ANCHOR_YEARS`, so the answer means something.

    `period_start`/`period_end` keep the untouched boundaries, so clamping
    loses no information — it only narrows what is asked about.
    """
    period_start, period_end = entry["start"], entry["end"]
    running = entry["status"] == "current" and period_end > as_of_date
    start, end = period_start, (as_of_date if running else period_end)
    age_at_start = entry.get("age_at_start")
    age_at_end = as_of_age if running else entry.get("age_at_end")
    if age_at_start is None or age_at_end is None:
        return None

    if age_at_start < _MIN_RECALL_AGE:
        start = _shift_date(start, _MIN_RECALL_AGE - age_at_start)
        age_at_start = float(_MIN_RECALL_AGE)
    if age_at_end - age_at_start > _MAX_ANCHOR_YEARS:
        start = _shift_date(end, -_MAX_ANCHOR_YEARS)
        age_at_start = round(age_at_end - _MAX_ANCHOR_YEARS, 1)
    if age_at_end - age_at_start < _MIN_ANCHOR_YEARS or start >= end:
        return None

    return {
        "label": entry["label"],
        "start": start,
        "end": end,
        "age_at_start": age_at_start,
        "age_at_end": age_at_end,
        "status": entry["status"],
        # So the model narrates "so far" rather than implying the period is
        # over, and so the real boundaries stay available.
        "in_progress": running,
        "period_start": period_start,
        "period_end": period_end,
        # True when the askable window is narrower than the period itself, so
        # the question can say "the last few years of that period" rather than
        # implying the whole of it.
        "partial_window": start != period_start or end != period_end,
        "window_years": round(age_at_end - age_at_start, 1),
    }


def _recallable(entry: dict, as_of_year: int) -> bool:
    """Whether a period is eligible to anchor a question at all.

    Only the checks `_anchor_from` cannot make: a window that has not started
    yet, and one that ended so long ago it will be answered vaguely if at all.
    The age floor deliberately does NOT live here any more — it applied to one
    generator of three while sitting in this function.
    """
    if entry["status"] == "upcoming":
        return False
    end_year = int(entry["end"][:4]) if entry["end"][:4].isdigit() else as_of_year
    return as_of_year - end_year <= _MAX_ANCHOR_AGE_YEARS


def _dasha_boundary_slots(bundle: dict, as_of_year: int, as_of_date: str,
                          as_of_age: float | None) -> list[dict]:
    """Periods whose lord is a wealth significator AND reads two ways.

    A dasha boundary is the strongest anchor available: it is a real dated
    transition in this reader's own chart, so the question is checkable
    ("did the money side change around then?") rather than a generality.
    """
    timeline = bundle.get("timeline") or {}
    slots = []
    for entry in timeline.get("entries") or []:
        if entry["kind"] not in ("mahadasha", "antardasha"):
            continue
        if not entry.get("domain_relevant") or not _recallable(entry, as_of_year):
            continue
        lord = entry.get("lord")
        placement = _lord_placement(bundle, lord)
        candidates = _divergent_candidates(bundle, lord, placement)
        if not candidates:
            continue
        anchor = _anchor_from(entry, as_of_date, as_of_age)
        if anchor is None:
            continue
        ruled = _and_list([_ord(c["house"]) for c in candidates if c["role"] == "ruled"])
        occupied = next(
            (c["house"] for c in candidates if c["role"] == "occupied"), None
        )
        slots.append({
            "slot_id": f"wealth.dasha_boundary.{lord}.{entry['start']}",
            "kind": "dasha_boundary",
            "anchor": anchor,
            "subject": lord,
            "ambiguity": (
                f"{lord} rules this chart's {ruled}"
                + (f" and occupies the {_ord(occupied)}" if occupied else "")
                + f". During the {entry['label']} ({entry['start']} to "
                f"{entry['end']}), each of those is a classically defensible "
                f"reading of what {lord} did to this reader's finances, and "
                "they imply different histories."
            ),
            "candidates": [*candidates, _NEITHER, _SKIP],
            "evidence": ["timeline", "houses", "dasha_relevance"],
            "why_it_changes_the_reading": (
                f"Which way {lord} actually expressed sets how every later "
                f"{lord} period in this chart should be read — including the "
                "ones still ahead."
            ),
            "priority": _priority(entry, candidates, base=0.8),
        })
    return slots


def _lord_placement(bundle: dict, planet: str | None) -> int | None:
    for row in bundle.get("houses") or []:
        placement = row.get("lord_placement") or {}
        if placement.get("planet") == planet:
            return placement.get("house")
    for brief in (bundle.get("karakas") or {}).values():
        if brief.get("planet") == planet:
            return brief.get("house")
    return None


def _significator_slots(bundle: dict, current_entry: dict | None,
                        as_of_date: str, as_of_age: float | None) -> list[dict]:
    """The 2nd and 11th lords themselves, independent of any dasha.

    A lifelong placement cannot be validated against "all your life" — the
    answer would be unfalsifiable — so these are anchored to the period the
    reader is currently living through, which is the stretch they can actually
    speak to.
    """
    if current_entry is None:
        return []
    slots = []
    for house in _PRIMARY_HOUSES:
        row = _house_row(bundle, house)
        if not row:
            continue
        lord = row.get("lord")
        placement = (row.get("lord_placement") or {}).get("house")
        candidates = _divergent_candidates(bundle, lord, placement)
        if not candidates:
            continue
        anchor = _anchor_from(current_entry, as_of_date, as_of_age)
        if anchor is None:
            continue
        slots.append({
            "slot_id": f"wealth.significator.h{house}.{lord}",
            "kind": "significator_placement",
            "anchor": anchor,
            "subject": lord,
            "ambiguity": (
                f"{lord} is this chart's {_ord(house)} lord and sits in the "
                f"{_ord(placement)}. It therefore has a defensible claim on "
                + " and on ".join(
                    f"the {_ord(c['house'])} ({c['gloss']})" for c in candidates
                )
                + ". Which of those it has actually delivered is not decidable "
                "from the chart alone."
            ),
            "candidates": [*candidates, _NEITHER, _SKIP],
            "evidence": ["houses", "timeline"],
            "why_it_changes_the_reading": (
                f"It fixes which house {lord} actually delivers from, which "
                "every wealth reading for this chart rests on."
            ),
            "priority": _priority(current_entry, candidates,
                                  base=0.9 if house in _PRIMARY_HOUSES else 0.6),
        })
    return slots


def _yoga_tension_slots(bundle: dict, current_entry: dict | None,
                        as_of_date: str, as_of_age: float | None) -> list[dict]:
    """An active wealth yoga sitting next to a wealth lord in a dusthana.

    The chart is carrying a gain signal and a retention problem at the same
    time. Both are real; the classical texts do not settle which dominates in a
    given life, and the reader does. This is also the slot most likely to catch
    a birth-time error, since a dusthana placement is house-sensitive.
    """
    if current_entry is None:
        return []
    active_yogas = [
        row for row in bundle.get("yogas") or []
        if row.get("active")
    ]
    if not active_yogas:
        return []
    strained = [
        row for row in bundle.get("houses") or []
        if row.get("house") in _PRIMARY_HOUSES and row.get("lord_in_dusthana")
    ]
    if not strained:
        return []
    anchor = _anchor_from(current_entry, as_of_date, as_of_age)
    if anchor is None:
        return []
    yoga = active_yogas[0]
    house_row = strained[0]
    house = house_row["house"]
    return [{
        "slot_id": f"wealth.yoga_tension.{yoga.get('rule_id')}.h{house}",
        "kind": "yoga_tension",
        "anchor": anchor,
        "subject": yoga.get("name"),
        "ambiguity": (
            f"{yoga.get('name')} is active in this chart, while the {house}th "
            f"lord {house_row.get('lord')} sits in a dusthana "
            f"({(house_row.get('lord_placement') or {}).get('house')}th). The "
            "chart is carrying a gain signal and a retention problem at once; "
            "which has actually dominated is not settled by the placement."
        ),
        "candidates": [
            {"key": "gain_dominant", "gloss":
             "income and opportunity have been the stronger story"},
            {"key": "retention_dominant", "gloss":
             "money has come in but not stayed — the retention side dominated"},
            {"key": "both", "gloss": "both, in alternating stretches"},
            _NEITHER, _SKIP,
        ],
        "evidence": ["yogas", "houses", "timeline"],
        "why_it_changes_the_reading": (
            "It decides whether this chart's advice is about earning more or "
            "about holding what already arrives — opposite readings from the "
            "same placements. A persistent miss here is also a birth-time "
            "signal, since the dusthana placement is house-sensitive."
        ),
        "priority": _priority(current_entry, [], base=0.85),
    }]


def _priority(entry: dict, candidates: list[dict], base: float) -> float:
    """Recency and primary-house weight, bounded to [0, 1].

    Nothing subtle here on purpose — it only has to produce a stable order for
    a list that gets truncated to two or three. A current period outranks a
    past one because the reader can speak to it in detail; a slot touching the
    2nd or 11th outranks one that does not.
    """
    score = base
    if entry.get("status") == "current":
        score += 0.1
    if any(c.get("house") in _PRIMARY_HOUSES for c in candidates):
        score += 0.05
    return round(min(score, 1.0), 3)


def validation_slots(bundle: dict, *, limit: int = 2,
                     exclude: set[str] | None = None) -> list[dict]:
    """The slots worth probing for this bundle, best first.

    `limit` is low by design and is the fatigue control. Every question spends
    the reader's patience, and a loop that asks five is worse than one that
    asks one — so this returns the best two, and the orchestrator asks a single
    one per turn.

    `exclude` is the "asked once" rule: a slot the reader has already answered
    for this chart never comes back.
    """
    if bundle.get("domain") != "wealth":
        return []
    exclude = exclude or set()
    timeline = bundle.get("timeline") or {}
    if not timeline.get("available"):
        return []
    # The current-period slots below are anchored to a window the reader is
    # living through, so they carry no `_recallable` check of their own — this
    # is where the same age floor applies to them.
    profile_facts = bundle.get("profile_facts") or {}
    if profile_facts.get("age_years", 0) < _MIN_RECALL_AGE:
        return []
    as_of_date = str(timeline.get("as_of", ""))[:10]
    as_of_age = profile_facts.get("age_years")
    as_of_year = int(str(timeline.get("as_of", ""))[:4] or 0)
    current_entry = next(
        (row for row in timeline.get("entries") or []
         if row["kind"] == "mahadasha" and row["status"] == "current"),
        None,
    )

    slots = [
        *_significator_slots(bundle, current_entry, as_of_date, as_of_age),
        *_yoga_tension_slots(bundle, current_entry, as_of_date, as_of_age),
        *_dasha_boundary_slots(bundle, as_of_year, as_of_date, as_of_age),
    ]
    # Same placement reached by two generators (a significator slot and a dasha
    # boundary slot can both land on the 11th lord) is one question, not two.
    #
    # The order of these three steps is load-bearing, and getting it wrong is
    # invisible until someone answers a question. A single combined check —
    # `if key in seen or slot_id in exclude: continue` — skips `seen.add()` for
    # an excluded slot, so answering a question removes the dedup barrier it
    # was providing and its suppressed twin surfaces on the next turn with an
    # identical subject and identical candidates. The reader is asked the same
    # thing twice in different words, which is precisely what "asked once"
    # exists to prevent. Dedup is a property of the slot set; exclusion is a
    # property of this reader's history. The first must be resolved before the
    # second is applied.
    seen: set[tuple] = set()
    unique = []
    for slot in slots:
        key = (slot["subject"], tuple(sorted(c["key"] for c in slot["candidates"])))
        if key in seen:
            continue
        seen.add(key)
        if slot["slot_id"] in exclude:
            continue
        slot["domain"] = "wealth"
        slot["source_status"] = "engine_selected"
        unique.append(slot)
    unique.sort(key=lambda s: (-s["priority"], s["slot_id"]))
    return unique[:limit]
