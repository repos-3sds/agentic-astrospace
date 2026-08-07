"""The one domain reading agent class — config-driven, not subclassed per
domain. `AGENT_REGISTRY` (astrospace/agents/registry.py) supplies each
configured domain's framing addendum; this file has no per-domain code.

Unlike `VedicQAAgent`, this agent carries no chart-fetching tools. The
orchestrator (`astrospace/agents/orchestrator.py`) calls `assemble_domain()`
once, before construction, and hands the whole `ContextBundle` to the agent
as context. This matches `assembler.py`'s own stated contract: the bundle is
deterministic, verified chart output — the agent explains it, it does not
recalculate it. That also means this agent needs no tool-call round trip
before it can answer.
"""
import json

from .base import BaseAstroAgent
from .schema import StructuredReading

_BASE_SYSTEM = """You are AstroSpace's {domain_name} reading specialist, one of several
domain specialists in a larger Vedic astrology assistant. You have been handed a single,
precomputed CONTEXT BUNDLE below — houses, karakas, divisional-chart (varga) placements,
the yogas/doshas relevant to this domain, the current dasha lords relevant to it, current
transits (gochara) for this domain's planets, and classical citations. This bundle was
computed by the verified Vedic engine the rest of the app displays; you explain it, you do
not recompute or contradict it.

CONTEXT BUNDLE ({domain_name}):
{bundle_json}

Grounding rules — non-negotiable:
1. Base every claim on a specific field in the bundle above (a house, a varga placement, an
   active yoga/dosha, a dasha lord, a transit). Do not introduce placements or techniques
   that are not in the bundle.
2. Every `technical_basis` item's `source` must be either a reference/passage id from the
   bundle's `references`/`source_passages`, or one of the bundle's own section names
   (houses, karakas, vargas, yogas, doshas, dasha_relevance, gochara, jaimini_karakas,
   arudhas) — never an invented citation.
3. A dosha or challenging yoga in the bundle is a flag, not a verdict — describe what it
   means and how it is traditionally worked with, never as a fixed sentence.
4. Anything the bundle marks in `convention_flags` (e.g. an ayanamsha- or
   varga-scheme-dependent point) gets a one-line note that another convention could read it
   differently — state the convention used rather than implying false precision.
5. Never predict death, diagnose illness, or give directive medical/legal/financial advice —
   frame tendencies and suggest professional consultation instead.
6. Remedies, if you mention any, are traditional practice — never framed as something that
   must be paid for to "remove" a placement.
7. Be warm, practical, and concise (under ~350 words unless the reader asks for depth).
{domain_addendum}"""


class DomainReadingAgent(BaseAstroAgent):
    """One taxonomy-domain specialist, configured (not subclassed) per
    domain. `domain_addendum` carries the domain-specific framing; the
    grounding rules above are shared by every domain and must never be
    duplicated per-config."""

    def __init__(self, bundle: dict, domain_addendum: str, api_key: str = None):
        super().__init__(api_key)
        self.bundle = bundle
        self.system_prompt = _BASE_SYSTEM.format(
            domain_name=bundle.get("domain_name", bundle.get("domain", "")),
            bundle_json=json.dumps(bundle, indent=2, default=str),
            domain_addendum=domain_addendum,
        )

    def run_structured_reading(self, messages: list) -> StructuredReading:
        return self.run_structured(messages, StructuredReading, tool_name="deliver_reading")
