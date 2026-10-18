"""Trims a domain bundle to what one kind of question needs.

`assemble_domain()` builds the same bundle for every question: every house,
karaka and varga for the domain, the reader's earlier dasha chapters, and up
to 50 book references. A broad question ("tell me about my career") uses all
of it. A narrow one ("should I take this offer?") gets a better answer from
less: the model stops reciting what it was handed.

Only reading material is dropped here. Every chart fact an answer can lean on
(houses, karakas, vargas, yogas, doshas, the running dasha, transits, the
reader's saved facts) stays, so grounding and the dosha rule are unchanged.
The verifier checks against this same trimmed bundle, so a citation to a
dropped reference is caught as ungrounded rather than silently accepted.
"""
from __future__ import annotations

import re

# How much reading material each kind of question gets. `broad` (and anything
# unknown) keeps the bundle untouched.
_LIMITS = {
    "today": {"references": 8, "source_passages": 3},
    "narrow": {"references": 12, "source_passages": 4},
    "explain": {"references": 15, "source_passages": 5},
}

_WORD = re.compile(r"[a-z]{4,}")


def _overlap(words: set[str], text: str) -> int:
    return len(words & set(_WORD.findall(text.casefold())))


def focus_bundle(bundle: dict, kind: str, question: str = "") -> dict:
    """A copy of `bundle` sized for `kind`. References are re-ranked by how
    many of the question's words they share (stable, so the knowledge base's
    own subdomain ranking breaks ties) before the cut."""
    limits = _LIMITS.get(kind)
    if limits is None:
        return bundle
    words = set(_WORD.findall(question.casefold()))
    focused = dict(bundle)

    references = list(bundle.get("references") or [])
    if words:
        references.sort(key=lambda ref: -_overlap(words, str(ref.get("statement", ""))))
    focused["references"] = references[:limits["references"]]
    focused["source_passages"] = list(bundle.get("source_passages") or [])[:limits["source_passages"]]

    # The dasha chapters before the previous one are life history: a broad or
    # "why did this happen" question uses them, a narrow one only recites them.
    retrospect = bundle.get("retrospect")
    if isinstance(retrospect, dict) and retrospect.get("earlier_chapters"):
        focused["retrospect"] = {**retrospect, "earlier_chapters": []}
    return focused
