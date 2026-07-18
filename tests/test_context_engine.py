"""Context Engine: taxonomy validation, assembly, routing, KB retrieval."""
import json

import pytest

from astrospace.context import (
    JsonKnowledgeBase, KeywordRouter, LLMRouter, assemble, assemble_domain,
    domain_ids, get_domain, get_knowledge_base, taxonomy,
)
from astrospace.context.taxonomy import TaxonomyError
from astrospace.core.vedic.chart import VedicChart

DELHI = {"city": "New Delhi", "nation": "IN"}


@pytest.fixture(scope="module")
def chart():
    return VedicChart("CE", 1990, 1, 1, 12, 0, **DELHI)


class TestTaxonomy:
    def test_all_domains_load_and_validate(self):
        specs = taxonomy()
        assert len(specs) == 10
        for spec in specs.values():
            assert spec.houses_primary
            assert spec.keywords
            assert spec.description

    def test_career_domain_shape(self):
        career = get_domain("career")
        assert 10 in career.houses_primary
        assert "Sun" in career.karakas_naisargika
        assert "AmK" in career.karakas_jaimini
        assert "D10" in career.vargas_primary

    def test_unknown_domain_raises(self):
        with pytest.raises(TaxonomyError):
            get_domain("gambling")

    def test_health_domain_carries_exclusions(self):
        health = get_domain("health")
        assert any("longevity" in e.lower() or "death" in e.lower()
                   for e in health.exclusions)


class TestAssembler:
    def test_career_bundle_structure(self, chart):
        bundle = assemble_domain(chart, "career", include_gochara=False)
        assert bundle["domain"] == "career"
        house_numbers = {row["house"] for row in bundle["houses"]}
        assert 10 in house_numbers
        tenth = next(row for row in bundle["houses"] if row["house"] == 10)
        assert tenth["tier"] == "primary"
        assert tenth["lord_placement"]["dignity"]
        assert "Sun" in bundle["karakas"]
        assert "AmK" in bundle["jaimini_karakas"]
        assert "D10" in bundle["vargas"]
        assert bundle["vargas"]["D10"]["tier"] == "primary"

    def test_yoga_filtering_is_domain_scoped(self, chart):
        career = assemble_domain(chart, "career", include_gochara=False)
        marriage = assemble_domain(chart, "marriage", include_gochara=False)
        career_ids = {row["rule_id"] for row in career["yogas"]}
        marriage_ids = {row["rule_id"] for row in marriage["doshas"]}
        assert "raja_yoga" in career_ids or "viparita_raja_yoga" in career_ids
        assert "manglik_dosha" in marriage_ids
        # Marriage bundle must not carry career yoga categories
        assert all(row.get("category") != "Power / Career" for row in marriage["yogas"])

    def test_dasha_relevance_chain(self, chart):
        bundle = assemble_domain(chart, "career", include_gochara=False)
        chain = bundle["dasha_relevance"]["chain"]
        levels = [row["level"] for row in chain]
        assert levels[:2] == ["mahadasha", "antardasha"]
        assert bundle["dasha_relevance"]["relevance"] in ("direct", "indirect")

    def test_gochara_scoped_to_domain_planets(self, chart):
        bundle = assemble_domain(chart, "marriage", include_gochara=True)
        gochara = bundle["gochara"]
        assert set(gochara["planets"]) <= {"Jupiter", "Saturn", "Rahu"}

    def test_full_bundle_multi_domain_and_serializable(self, chart):
        bundle = assemble(chart, ["marriage", "foreign"],
                          question="Will I settle abroad after marriage?")
        assert bundle["domains"][0]["domain"] == "marriage"
        assert bundle["domains"][0]["tier"] == "primary"
        assert bundle["domains"][1]["domain"] == "foreign"
        assert bundle["domains"][1]["tier"] == "secondary"
        assert bundle["chart_identity"]["lagna"]
        # Must round-trip through JSON for LangGraph state / API payloads.
        assert json.loads(json.dumps(bundle))["question"].startswith("Will I")

    def test_references_attached_with_citations(self, chart):
        bundle = assemble_domain(chart, "career", include_gochara=False)
        assert bundle["references"], "seed KB should supply career references"
        ref = bundle["references"][0]
        assert ref["source_text_key"]
        assert ref["statement"]


class TestRouter:
    def test_career_question(self):
        decision = KeywordRouter().route("When will I get a promotion in my job?")
        assert decision.primary == "career"
        assert decision.confidence in ("medium", "high")

    def test_multi_domain_question(self):
        decision = KeywordRouter().route("Will I settle abroad after marriage?")
        assert {decision.primary, *decision.secondary} >= {"marriage", "foreign"}

    def test_no_keywords_falls_back_to_default(self):
        decision = KeywordRouter().route("Tell me something interesting")
        assert decision.method == "default"
        assert decision.primary in domain_ids()

    def test_llm_router_uses_classifier_and_falls_back(self):
        router = LLMRouter(lambda q, catalog: ["health"])
        assert router.route("anything").primary == "health"
        broken = LLMRouter(lambda q, catalog: (_ for _ in ()).throw(RuntimeError()))
        assert broken.route("court case against my rival").primary == "litigation"


class TestKnowledgeBase:
    def test_retrieve_by_domain(self):
        kb = get_knowledge_base()
        refs = kb.retrieve(["career"])
        assert refs and all("career" in r.domains for r in refs)

    def test_subdomain_ranking(self):
        kb = get_knowledge_base()
        refs = kb.retrieve(["career"], subdomains=["field_selection"])
        assert refs[0].ref_id == "bphs_d10_career"

    def test_sources_catalog_has_bibliography(self):
        catalog = get_knowledge_base().sources_catalog()
        assert "uttara_kalamrita" in catalog
        assert "translation" in catalog["uttara_kalamrita"]

    def test_multi_domain_reference(self):
        kb = get_knowledge_base()
        health = kb.retrieve(["health"])
        litigation = kb.retrieve(["litigation"])
        shared = {r.ref_id for r in health} & {r.ref_id for r in litigation}
        assert "pm_disease_sixth" in shared


class TestGraphIntegration:
    def test_graph_module_importable_without_langgraph(self):
        # The module itself must import cleanly; only build_reading_graph
        # requires the optional dependency.
        from astrospace.context.graph import ReadingState, build_reading_graph
        assert build_reading_graph is not None
        assert "question" in ReadingState.__annotations__
