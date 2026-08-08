"""Runnable domain-agent registry — configured agents only.

Deliberately does NOT list all 10 taxonomy domains. `taxonomy.py` already
owns the full domain catalog (names, houses, vargas, keywords); this module
owns only "which of those domains actually has a working specialist right
now." A routed domain absent here is `domain_not_ready` — the orchestrator
gets the display name straight from `taxonomy.get_domain(id).name`, so no
placeholder rows are needed for the other 8.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    domain_id: str
    domain_addendum: str


_CAREER_ADDENDUM = """
Career-specific framing:
- The 10th house/lord and D10 (dashamsa) placements are the primary evidence for career
  questions; the 6th (competition/service), 2nd/11th (income), and 7th (partnerships/
  business) houses are supporting evidence, not the headline.
- "Should I take this job" or "should I start a business" style questions: describe what
  the bundle supports (e.g. a strong 10th lord in D10 favouring authority roles) rather than
  issuing a directive — the reader decides, you supply the astrological reasoning.
- Timing questions (job change, promotion) should be answered from the dasha_relevance and
  gochara sections' actual lords/transits in the bundle, not general trends."""

_MARRIAGE_ADDENDUM = """
Marriage-specific framing:
- The 7th house/lord and D9 (navamsa) placements are the primary evidence for marriage
  questions; Venus/Jupiter/Mars (this domain's karakas) and the 2nd/4th/8th/12th houses are
  supporting evidence, not the headline.
- Manglik dosha (mangal/kuja dosha), gandanta dosha, or grahan dosha in the bundle are flags
  to describe and contextualise — never a verdict. Never say a dosha means marriage cannot
  happen, will end in divorce, or will fail; never claim a spouse "cannot be found." Describe
  what the classical texts say the flag traditionally calls for (care in matching, timing,
  or a specific remedy), not a fixed outcome.
- Arranged-vs-love framing, compatibility, and delay-vs-denial questions: describe what the
  bundle supports rather than issuing a directive about which path to take or whether to
  proceed with a specific match — the reader decides.
- Timing questions (when marriage is likely, whether this is a good year) should be answered
  from the dasha_relevance and gochara sections' actual lords/transits in the bundle, not
  general trends."""

_WEALTH_ADDENDUM = """
Wealth-specific framing:
- The 2nd (accumulated wealth) and 11th (gains/income) houses and lords are the primary evidence
  for wealth questions; the 9th (fortune), 5th (speculation), and D2 (hora) chart placements
  are supporting evidence, not the headline.
- "Should I buy/sell/invest in this specific stock/property" style questions are strictly blocked
  by safety.py's refer_out_kind() boundary, as they seek directive financial advice. Frame your
  analysis around timing and astrological suitability (e.g., "is this a good year for my finances").
- When answering questions, describe what the bundle supports (e.g. strong 11th lord indicating
  potential for gains) rather than issuing financial directives — the reader decides, you supply
  the astrological reasoning.
- Timing questions (when financial situation will improve) should be answered from the
  dasha_relevance and gochara sections' actual lords/transits in the bundle, not general trends."""


AGENT_REGISTRY: dict[str, AgentConfig] = {
    "career": AgentConfig(domain_id="career", domain_addendum=_CAREER_ADDENDUM),
    "marriage": AgentConfig(domain_id="marriage", domain_addendum=_MARRIAGE_ADDENDUM),
    "wealth": AgentConfig(domain_id="wealth", domain_addendum=_WEALTH_ADDENDUM),
}
