"""
Question → domain routing.

Two implementations behind one contract:
- KeywordRouter: deterministic, zero-cost fallback using taxonomy keywords.
- LLMRouter: wraps any callable(question, domain_catalog) -> domain ids, so the
  model/provider choice stays outside this module (inject a Haiku call, a
  LangGraph node, whatever). Falls back to KeywordRouter on failure.

Multi-domain by design: "will I settle abroad after marriage?" routes to
marriage (primary) + foreign (secondary).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Protocol

from .taxonomy import domain_ids, taxonomy


@dataclass(frozen=True)
class RoutingDecision:
    primary: str
    secondary: tuple[str, ...] = field(default=())
    confidence: str = "low"          # low | medium | high
    method: str = "keyword"          # keyword | llm | default
    matched_terms: tuple[str, ...] = field(default=())

    @property
    def domains(self) -> list[str]:
        return [self.primary, *self.secondary]


class Router(Protocol):
    def route(self, question: str) -> RoutingDecision: ...


DEFAULT_DOMAIN = "career"  # safest general life-direction bucket for v1


class KeywordRouter:
    """Scores each domain by keyword hits (whole-word, case-insensitive).
    Primary = top score; secondaries = other domains with >= 1 hit."""

    def route(self, question: str) -> RoutingDecision:
        text = question.lower()
        scores: dict[str, list[str]] = {}
        for domain_id, spec in taxonomy().items():
            hits = [
                kw for kw in spec.keywords
                if re.search(rf"\b{re.escape(kw)}\b", text)
            ]
            if hits:
                scores[domain_id] = hits
        if not scores:
            return RoutingDecision(primary=DEFAULT_DOMAIN, confidence="low",
                                   method="default")
        ranked = sorted(scores.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        primary, primary_hits = ranked[0]
        secondary = tuple(domain_id for domain_id, _ in ranked[1:3])
        confidence = "high" if len(primary_hits) >= 2 else "medium"
        return RoutingDecision(
            primary=primary, secondary=secondary, confidence=confidence,
            method="keyword", matched_terms=tuple(primary_hits),
        )


class LLMRouter:
    """classify: (question, catalog) -> list of domain ids, best first.
    catalog is {domain_id: description}. Any error or invalid output falls
    back to the keyword router — routing must never take a reading down."""

    def __init__(self, classify: Callable[[str, dict[str, str]], list[str]]):
        self._classify = classify
        self._fallback = KeywordRouter()

    def route(self, question: str) -> RoutingDecision:
        catalog = {d: spec.description for d, spec in taxonomy().items()}
        try:
            picked = [d for d in self._classify(question, catalog)
                      if d in domain_ids()]
        except Exception:
            picked = []
        if not picked:
            return self._fallback.route(question)
        return RoutingDecision(
            primary=picked[0], secondary=tuple(picked[1:3]),
            confidence="high", method="llm",
        )
