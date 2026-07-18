"""
Reference knowledge base for the Context Engine.

A Reference is one classical rule/signification with its citation — encoded as
structured data (never copied translation text; translations are copyrighted,
the rules are not). The store backend is pluggable behind KnowledgeBase so the
JSON file used today can be swapped for pgvector/semantic retrieval later
without touching the assembler or agents.

references.json entry schema:
  {
    "ref_id": "uk_4_career_10th",
    "domains": ["career"],
    "subdomains": ["job_vs_business"],
    "statement": "The 10th bhava governs livelihood, rank, honour and karma.",
    "source": {"text_key": "uttara_kalamrita", "location": "Kanda 4"},
    "tags": ["house:10"],
    "status": "verified_common" | "convention_dependent" | "needs_review"
  }
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Protocol

BASE = Path(__file__).parent


@dataclass(frozen=True)
class Reference:
    ref_id: str
    domains: tuple[str, ...]
    statement: str
    source_text_key: str
    source_location: str
    subdomains: tuple[str, ...] = field(default=())
    tags: tuple[str, ...] = field(default=())
    status: str = "needs_review"

    def to_dict(self) -> dict:
        return asdict(self)


class KnowledgeBase(Protocol):
    """Retrieval contract — implement this to swap in a semantic backend."""

    def retrieve(self, domains: list[str], subdomains: list[str] | None = None,
                 tags: list[str] | None = None, limit: int = 20) -> list[Reference]:
        ...

    def sources_catalog(self) -> dict:
        """{text_key: bibliographic entry} for citation rendering."""
        ...


class JsonKnowledgeBase:
    """File-backed KB. Metadata-filtered lookup — no embeddings needed while
    the corpus is structured rules. Ranking: domain match, then subdomain
    match count, then tag match count, then verified status."""

    def __init__(self, references_path: Path | None = None,
                 sources_path: Path | None = None):
        self._references_path = references_path or BASE / "references.json"
        self._sources_path = sources_path or BASE / "sources.json"

    @lru_cache(maxsize=1)
    def _load(self) -> list[Reference]:
        if not self._references_path.exists():
            return []
        payload = json.loads(self._references_path.read_text())
        out = []
        for raw in payload.get("references", []):
            out.append(Reference(
                ref_id=raw["ref_id"],
                domains=tuple(raw.get("domains", [])),
                statement=raw["statement"],
                source_text_key=raw["source"]["text_key"],
                source_location=raw["source"].get("location", ""),
                subdomains=tuple(raw.get("subdomains", [])),
                tags=tuple(raw.get("tags", [])),
                status=raw.get("status", "needs_review"),
            ))
        return out

    def retrieve(self, domains: list[str], subdomains: list[str] | None = None,
                 tags: list[str] | None = None, limit: int = 20) -> list[Reference]:
        domain_set = set(domains)
        sub_set = set(subdomains or [])
        tag_set = set(tags or [])
        _status_rank = {"verified_common": 0, "convention_dependent": 1, "needs_review": 2}

        scored = []
        for ref in self._load():
            if not domain_set & set(ref.domains):
                continue
            sub_hits = len(sub_set & set(ref.subdomains))
            tag_hits = len(tag_set & set(ref.tags))
            scored.append(((-sub_hits, -tag_hits, _status_rank.get(ref.status, 3)), ref))
        scored.sort(key=lambda pair: pair[0])
        return [ref for _, ref in scored[:limit]]

    def sources_catalog(self) -> dict:
        if not self._sources_path.exists():
            return {}
        return json.loads(self._sources_path.read_text()).get("sources", {})


_default_kb: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    global _default_kb
    if _default_kb is None:
        _default_kb = JsonKnowledgeBase()
    return _default_kb


def set_knowledge_base(kb: KnowledgeBase) -> None:
    """Swap the backend (e.g., a pgvector implementation) app-wide."""
    global _default_kb
    _default_kb = kb
