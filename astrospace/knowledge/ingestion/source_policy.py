from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceEnrichment:
    source_domains: tuple[str, ...] = ()
    topics: tuple[str, ...] = ()
    quality_notes: tuple[str, ...] = ()


def source_enrichment(source_key: str) -> SourceEnrichment:
    """Return deterministic provenance policy for edition-sensitive sources."""
    normalized = source_key.strip().lower()
    if normalized == "lal-kitab" or normalized.startswith("lal-kitab-"):
        return SourceEnrichment(
            source_domains=("lal_kitab_tradition", "traditional_remedies"),
            topics=("lal_kitab_remedies",),
            quality_notes=(
                "Lal Kitab passage requires edition-aware human review before publication",
            ),
        )
    return SourceEnrichment()
