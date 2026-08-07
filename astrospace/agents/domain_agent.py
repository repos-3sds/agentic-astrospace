"""Domain reading agents — one specialist per Context Engine taxonomy domain.

Unlike `VedicQAAgent`, these carry no chart-fetching tools. The orchestrator
(`astrospace/api/ask_stream_routes.py`) calls `assemble_domain()` once,
before construction, and hands the whole `ContextBundle` to the agent as
context. This matches `assembler.py`'s own stated contract: the bundle is
deterministic, verified chart output — the agent explains it, it does not
recalculate it. That also means these agents need no tool-call round trip
before they can start streaming an answer.
"""
import json

from .base import BaseAstroAgent

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
2. When you use a classical citation from `references` or `source_passages`, name it by its
   `source_key` (or `book`) so the reader can see where a claim comes from.
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
    """Base for one taxonomy-domain specialist. Subclasses set
    `domain_addendum` for domain-specific framing; the grounding rules above
    are shared by every domain and must not be duplicated per-subclass."""

    domain_addendum = ""

    def __init__(self, bundle: dict, api_key: str = None):
        super().__init__(api_key)
        self.bundle = bundle
        self.system_prompt = _BASE_SYSTEM.format(
            domain_name=bundle.get("domain_name", bundle.get("domain", "")),
            bundle_json=json.dumps(bundle, indent=2, default=str),
            domain_addendum=self.domain_addendum,
        )


class CareerReadingAgent(DomainReadingAgent):
    domain_addendum = """
Career-specific framing:
- The 10th house/lord and D10 (dashamsa) placements are the primary evidence for career
  questions; the 6th (competition/service), 2nd/11th (income), and 7th (partnerships/
  business) houses are supporting evidence, not the headline.
- "Should I take this job" or "should I start a business" style questions: describe what
  the bundle supports (e.g. a strong 10th lord in D10 favouring authority roles) rather than
  issuing a directive — the reader decides, you supply the astrological reasoning.
- Timing questions (job change, promotion) should be answered from the dasha_relevance and
  gochara sections' actual lords/transits in the bundle, not general trends."""


# Registry the orchestrator dispatches through. Future domains add themselves
# here once they have a working specialist; a domain with no entry falls back
# to the general-purpose VedicQAAgent.
DOMAIN_AGENTS: dict[str, type[DomainReadingAgent]] = {
    "career": CareerReadingAgent,
}
