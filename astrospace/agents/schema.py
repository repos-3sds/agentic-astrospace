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
                    "jaimini_karakas, arudhas) — never an invented citation."
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
