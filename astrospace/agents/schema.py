"""The structured reading contract every domain agent answers in.

Content only. `status`, `schema_version`, `domain`, `intent`, `context_used`,
`evidence_refs`, and verification outcome are envelope fields the
orchestrator computes — the model is never trusted to self-report anything
about its own correctness, only to produce the consultation itself. See
`astrospace/agents/orchestrator.py`.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AskIntent = Literal[
    "timing", "suitability", "explanation", "remedy",
    "comparison", "daily_guidance", "general_guidance",
]


class TechnicalBasisItem(BaseModel):
    factor: str = Field(description="The chart factor being cited, e.g. '10th lord Mercury' or 'Moon pratyantardasha'.")
    reading: str = Field(description="What that factor means for this domain — the technical interpretation.")
    source: str = Field(
        description="Either a KB reference/passage id from the context bundle's `references`/"
                    "`source_passages`, or one of the bundle's own section names "
                    "(houses, karakas, vargas, yogas, doshas, dasha_relevance, gochara, "
                    "jaimini_karakas, arudhas, profile_facts) — never an invented citation."
    )


class RemedyItem(BaseModel):
    practice: str = Field(description="A traditional practice — never framed as paid removal of a placement.")
    note: str = Field(description="Context for why this practice is traditionally associated with the factor.")


class Guidance(BaseModel):
    practical_actions: list[str] = Field(default_factory=list)
    remedies: list[RemedyItem] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)


class StructuredReading(BaseModel):
    """The 5-beat consultation structure: acknowledge, ground, interpret,
    reassure, guide. Every domain agent answers through this same shape."""
    acknowledgment: str = Field(description="Reflects the actual question back — proves it was understood.")
    technical_basis: list[TechnicalBasisItem] = Field(
        description="The chart evidence behind the reading — grounds the interpretation in the bundle, not memory."
    )
    interpretation: str = Field(description="The empathetic, plain-language explanation or prediction — the heart of the reading.")
    summary_and_assurance: str = Field(description="A short, grounding close — not a fixed sentence, the constructive angle.")
    guidance: Guidance
    confidence: Literal["high", "medium", "low"]


def reading_tool_schema(allowed_sources: set[str]) -> dict:
    """`StructuredReading`'s JSON Schema with `technical_basis[].source`
    narrowed to an enum of exactly the sources this request's bundle can
    support.

    The point is to move the most common failure class from *detected* to
    *impossible*. Before this, `source` was a free-form string, and an
    invented citation was caught only after generation — by
    `verifier.valid_sources()` — which cost a full second generation through
    `AskOrchestrator._agent_run_and_verify()`'s repair path. An enum in the
    tool definition makes the model unable to emit one in the first place.

    Two properties this depends on, both load-bearing:

    - `allowed_sources` MUST come from `verifier.valid_sources()`, never be
      re-derived here. A constraint that disagrees with its own checker is
      worse than no constraint: whichever side is looser wins silently.
    - The bundle is fixed and known before generation (ADR-001's kept
      property — the agent has no tools and fetches no context of its own),
      which is the only reason the valid set is computable up front at all.
      This reinforces that decision rather than eroding it.

    This is a decoding constraint, not a checker, so it does not touch the
    "the checker must not be the same generation context grading itself"
    principle — `verify()` still runs afterwards, unchanged, and still
    rejects an out-of-set source if a provider ever ignores the enum.

    Honest cost: the enum restates every reference/passage id already
    present in the bundle, so it *adds* input tokens (measured at ~1.2 KB
    on a career bundle). That is a deliberate trade against a repair round
    trip that costs an entire second reading — it is a latency win, not a
    payload win, and should not be mistaken for one.
    """
    schema = StructuredReading.model_json_schema()
    source = schema["$defs"]["TechnicalBasisItem"]["properties"]["source"]
    # Sorted for a stable, cacheable schema — an unordered set would produce
    # a different tool definition on every request for the same bundle.
    source["enum"] = sorted(allowed_sources)
    return schema
