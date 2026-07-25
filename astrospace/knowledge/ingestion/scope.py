from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ScopeDecision:
    scope: str
    confidence: float
    reason: str | None
    classifier: str


_CURATED_RANGES: dict[str, tuple[tuple[int, int, str, str], ...]] = {
    "brihat-jataka": (
        (0, 0, "publishing", "title and publication page"),
        (1, 5, "navigation", "table of contents"),
        (6, 11, "editorial", "translator preface and introduction"),
        (355, 358, "editorial", "translator autobiography and genealogy"),
    ),
    "brihat-parasara-hora-sastra-volume-1": (
        (0, 0, "publishing", "title and publication pages"),
        (1, 3, "navigation", "table of contents"),
        (4, 4, "editorial", "translator preface"),
    ),
    "phaladeepika-mantreswara": (
        (0, 0, "publishing", "title, library and publication pages"),
        (1, 22, "navigation", "contents and descriptive contents"),
        (180, 309, "navigation", "Sanskrit and English indexes"),
    ),
    "saravali-kalyana-varma": (
        (0, 0, "publishing", "title and publication pages"),
        (1, 1, "editorial", "translator note"),
        (2, 8, "publishing", "publisher catalogue"),
        (9, 15, "navigation", "chapter index and catalogue list"),
        (16, 16, "editorial", "modern editorial introduction"),
        (199, 199, "publishing", "next-volume advertisement"),
    ),
    "uttara-kalamritam": (
        (0, 0, "publishing", "title, publication and preface pages"),
        (1, 8, "navigation", "table of contents"),
        (150, 186, "out_of_domain", "non-astrological ritual and dharma section"),
        (187, 187, "publishing", "publisher special offer"),
    ),
}


def classify_retrieval_scope(
    source_key: str,
    ordinal: int,
    title: str,
    content: str,
) -> ScopeDecision:
    for start, end, scope, reason in _CURATED_RANGES.get(source_key, ()):
        if start <= ordinal <= end:
            return ScopeDecision(scope, 0.99, reason, "curated-edition-boundaries-v1")

    normalized_title = re.sub(r"\s+", " ", title).strip().lower()
    sample = re.sub(r"\s+", " ", content[:1500]).lower()
    if normalized_title in {"contents", "table of contents", "index"}:
        return ScopeDecision(
            "navigation", 0.94, normalized_title, "structural-scope-v1",
        )
    if normalized_title.startswith(("preface", "foreword")):
        return ScopeDecision(
            "editorial", 0.92, normalized_title, "structural-scope-v1",
        )
    if "special offer" in normalized_title or "send for our catalogue" in sample:
        return ScopeDecision(
            "publishing", 0.96, "publisher promotion", "structural-scope-v1",
        )
    return ScopeDecision("core", 0.70, None, "structural-scope-v1")
