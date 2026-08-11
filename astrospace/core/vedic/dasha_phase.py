"""Where inside a dasha its effects fall — BPHS 47.3-4.

A mahadasha can run sixteen years. Naming the whole span and stopping is what
makes a reading sound like a newspaper column: technically true of a period long
enough that anything might happen in it. Parasara is more specific than we have
been.

The rule (Brihat Parasara Hora Shastra, ch.47 shlokas 3-4, Santhanam translation,
printed p.453) keys on the dasha lord's DREKKANA — which third of its sign the
planet occupies:

    1st drekkana  ->  effects felt at the COMMENCEMENT of the dasha
    2nd drekkana  ->  felt in the MIDDLE
    3rd drekkana  ->  felt at the END

and then reverses the order for a retrograde planet: retrograde in the 3rd
drekkana delivers at the start, retrograde in the 1st delivers at the end. The
middle is its own mirror image and does not move.

Rahu and Ketu are always retrograde, so their emphasis is always reversed. That
is not a special case in this module — `positions.py` already reports them as
retrograde, so the general rule produces it.

WHAT THIS IS NOT. It does not say the rest of the dasha is empty, and it does
not predict an event on a date. It says where the weight sits. Phrase it as
emphasis ("the weight of this falls in the closing years"), never as a boundary
("nothing happens until 2031").
"""
from __future__ import annotations

from datetime import datetime

from .vargas import _parts

__all__ = ["dasha_emphasis", "emphasis_window", "annotate_emphasis"]

# Index 0/1/2 = 1st/2nd/3rd drekkana, direct motion.
_DIRECT = ("early", "middle", "late")
# Retrograde reverses the order. "middle" is its own mirror.
_RETROGRADE = ("late", "middle", "early")

_SOURCE = "BPHS 47.3-4 (Santhanam, p.453)"


def dasha_emphasis(lon: float, retrograde: bool) -> dict:
    """Which third of its dasha a lord at `lon` carries the weight in.

    `lon` is the planet's sidereal longitude at BIRTH — the natal drekkana is
    what the rule keys on. `retrograde` likewise natal.
    """
    drekkana_index = _parts(lon, 3)[1]  # 0, 1 or 2
    phase = (_RETROGRADE if retrograde else _DIRECT)[drekkana_index]
    return {
        "drekkana": drekkana_index + 1,
        "retrograde": bool(retrograde),
        "phase": phase,
        "rule": (
            f"{drekkana_index + 1}"
            f"{'st' if drekkana_index == 0 else 'nd' if drekkana_index == 1 else 'rd'}"
            f" drekkana{', retrograde (order reversed)' if retrograde else ''}"
            f" -> weight falls {phase} in the period"
        ),
        "source": _SOURCE,
    }


def _as_datetime(value: datetime | str) -> datetime:
    """Dasha periods carry ISO strings (see `dashas._period`), not datetimes.

    Accepting both matters: an isinstance check against `datetime` alone looks
    correct and silently never fires against the real timeline, so the window
    would be quietly absent everywhere rather than wrong somewhere.
    """
    return value if isinstance(value, datetime) else datetime.fromisoformat(value)


def emphasis_window(start: datetime | str, end: datetime | str, phase: str) -> dict:
    """The third of [start, end] that `phase` names, as ISO dates.

    Thirds by elapsed time, not by sub-period count: the rule is about the span,
    and antardashas within a mahadasha are of markedly unequal length, so
    counting them would put the "middle" in a different place depending on which
    lord happened to start the chain.

    Returns ISO strings to match the surrounding dasha dict, which is
    JSON-serialised into the bundle.
    """
    lo_dt, hi_dt = _as_datetime(start), _as_datetime(end)
    if hi_dt <= lo_dt:
        raise ValueError(f"dasha end {end} is not after start {start}")
    span = (hi_dt - lo_dt) / 3
    bounds = {
        "early": (lo_dt, lo_dt + span),
        "middle": (lo_dt + span, lo_dt + 2 * span),
        "late": (lo_dt + 2 * span, hi_dt),
    }
    if phase not in bounds:
        raise ValueError(f"unknown phase {phase!r}; expected one of {sorted(bounds)}")
    lo, hi = bounds[phase]
    return {"from": lo.isoformat(), "to": hi.isoformat()}


def annotate_emphasis(mahadashas: list[dict], positions: dict) -> list[dict]:
    """Attach `emphasis` to each mahadasha that has a natal position for its lord.

    Returns new dicts; the input is not mutated, because the dasha timeline is
    shared with callers that pin it in tests.

    A lord with no entry in `positions` is skipped rather than guessed at — the
    annotation is absent, not defaulted, so a caller can tell "not computable"
    from "falls early".
    """
    out = []
    for period in mahadashas:
        lord = period.get("lord")
        natal = positions.get(lord)
        annotated = dict(period)
        if natal and "lon" in natal:
            emphasis = dasha_emphasis(natal["lon"], bool(natal.get("retrograde")))
            start, end = period.get("start"), period.get("end")
            if start and end:
                try:
                    emphasis["window"] = emphasis_window(start, end, emphasis["phase"])
                except ValueError:
                    # A zero-length or unparseable period: the phase still holds,
                    # the dates do not. Omit the window rather than invent one.
                    pass
            annotated["emphasis"] = emphasis
        out.append(annotated)
    return out
