"""AstroSpace Context Engine — domain-scoped chart context assembly.

Public surface:
    taxonomy(), get_domain(), domain_ids()   — domain registry (data-driven)
    assemble(chart, domains, question=...)   — build a ContextBundle dict
    KeywordRouter / LLMRouter                — question -> domains
    get_knowledge_base() / set_knowledge_base — pluggable reference store
    build_reading_graph                      — optional LangGraph orchestration
"""
from .assembler import assemble, assemble_domain
from .daily import assemble_daily_context, daily_guidance
from .graph import ReadingState, build_reading_graph
from .kb import JsonKnowledgeBase, Reference, get_knowledge_base, set_knowledge_base
from .router import KeywordRouter, LLMRouter, RoutingDecision
from .subdomain_match import match_subdomains
from .taxonomy import DomainSpec, TaxonomyError, domain_ids, get_domain, taxonomy

__all__ = [
    "assemble", "assemble_domain",
    "assemble_daily_context", "daily_guidance",
    "JsonKnowledgeBase", "Reference", "get_knowledge_base", "set_knowledge_base",
    "KeywordRouter", "LLMRouter", "RoutingDecision",
    "match_subdomains",
    "ReadingState", "build_reading_graph",
    "DomainSpec", "TaxonomyError", "domain_ids", "get_domain", "taxonomy",
]
