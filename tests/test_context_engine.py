"""Context Engine: taxonomy validation, assembly, routing, KB retrieval."""
import json
from datetime import datetime, timezone

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
        assert len(specs) == 11
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

    def test_personality_domain_shape(self):
        personality = get_domain("personality")
        assert 1 in personality.houses_primary
        assert "Sun" in personality.karakas_naisargika
        assert "Moon" in personality.karakas_naisargika
        assert "Mercury" in personality.karakas_naisargika
        assert "AK" in personality.karakas_jaimini
        assert "D1" in personality.vargas_primary

    def test_unknown_domain_raises(self):
        with pytest.raises(TaxonomyError):
            get_domain("gambling")

    def test_health_domain_carries_exclusions(self):
        health = get_domain("health")
        assert any("longevity" in e.lower() or "death" in e.lower()
                   for e in health.exclusions)

    def test_personality_domain_carries_a_mental_health_exclusion(self):
        """This domain sits right next to health's mental-health refer-out
        boundary (safety.py's `mental (?:health|illness)` subject) — the
        taxonomy itself must say, in its own exclusions, that it is not a
        clinical/psychological assessment."""
        personality = get_domain("personality")
        assert any("clinical" in e.lower() or "mental-health" in e.lower()
                   or "mental health" in e.lower() or "psychological" in e.lower()
                   for e in personality.exclusions)


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

    def test_house_lord_dignity_carries_its_own_reasoning(self, chart):
        """A domain agent should be able to cite *why* a lord's dignity
        landed where it did, not just assert the label — dignity_reasoning
        exposes the dispositor plus both the natural and temporal
        relationship that the compound dignity was derived from."""
        bundle = assemble_domain(chart, "career", include_gochara=False)
        reasoned = [row for row in bundle["houses"]
                    if "dignity_reasoning" in row["lord_placement"]]
        assert reasoned, "expected at least one house lord with a dispositor relationship"
        reasoning = reasoned[0]["lord_placement"]["dignity_reasoning"]
        assert reasoning["dispositor"]
        assert reasoning["natural_relation"] in ("friend", "enemy", "neutral")
        assert reasoning["temporal_relation"] in ("friend", "enemy")
        # Direct sign matches (Exalted/Debilitated/Moolatrikona/Own) have no
        # dispositor relationship to reason about, so the key is absent
        # rather than null — confirm both shapes actually occur.
        direct = [row for row in bundle["houses"]
                  if row["lord_placement"]["dignity"] in
                  ("Exalted", "Debilitated", "Moolatrikona", "Own")]
        if direct:
            assert "dignity_reasoning" not in direct[0]["lord_placement"]

    def test_house_lord_carries_dhatu_and_rasa(self, chart):
        """Health & Longevity's taxonomy scope claims Ayurvedic-constitution
        framing; dhatu/rasa give it real data to ground that in instead of
        the model inventing or recalling it from training data."""
        bundle = assemble_domain(chart, "health", include_gochara=False)
        with_dhatu = [row for row in bundle["houses"]
                      if "dhatu" in row["lord_placement"]]
        assert with_dhatu, "expected at least one house lord to carry dhatu/rasa"
        lord = with_dhatu[0]["lord_placement"]
        assert lord["dhatu"]
        assert lord["rasa"]

    def test_nodes_have_no_fabricated_dhatu_or_rasa(self, chart):
        """Rahu/Ketu genuinely have no classical dhatu/rasa assignment —
        confirm the field is absent, not a guessed/fabricated value."""
        from astrospace.core.vedic.constants import PLANET_DHATU, PLANET_RASA
        assert "Rahu" not in PLANET_DHATU and "Ketu" not in PLANET_DHATU
        assert "Rahu" not in PLANET_RASA and "Ketu" not in PLANET_RASA

    def test_profile_facts_are_deterministic_not_left_to_the_model(self, chart):
        """Item 3 requirement (docs/ask_context_engine_multi_agent_
        architecture_2026-08-07.md, "Update 2026-08-09"): age must be
        computed once in the backend, not left for the model to derive
        from birth data + as_of itself."""
        as_of = datetime(2026, 1, 1, tzinfo=timezone.utc)
        bundle = assemble_domain(chart, "career", include_gochara=False, as_of=as_of)
        facts = bundle["profile_facts"]
        assert facts["birth_year"] == 1990
        assert facts["age_years"] == pytest.approx(36.0, abs=0.1)
        assert facts["as_of"].startswith("2026-01-01")

    def test_yoga_filtering_is_domain_scoped(self, chart):
        career = assemble_domain(chart, "career", include_gochara=False)
        marriage = assemble_domain(chart, "marriage", include_gochara=False)
        career_ids = {row["rule_id"] for row in career["yogas"]}
        marriage_ids = {row["rule_id"] for row in marriage["doshas"]}
        assert "raja_yoga" in career_ids or "viparita_raja_yoga" in career_ids
        assert "manglik_dosha" in marriage_ids
        # Marriage bundle must not carry career yoga categories
        assert all(row.get("category") != "Power / Career" for row in marriage["yogas"])

    def test_personality_bundle_structure(self, chart):
        bundle = assemble_domain(chart, "personality", include_gochara=False)
        assert bundle["domain"] == "personality"
        house_numbers = {row["house"] for row in bundle["houses"]}
        assert 1 in house_numbers
        first = next(row for row in bundle["houses"] if row["house"] == 1)
        assert first["tier"] == "primary"
        assert first["lord_placement"]["dignity"]
        assert {"Sun", "Moon", "Mercury"} <= set(bundle["karakas"])
        assert "AK" in bundle["jaimini_karakas"]
        assert "D1" in bundle["vargas"]
        assert bundle["vargas"]["D1"]["tier"] == "primary"

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

    def test_gochara_active_rules_carry_real_transit_windows(self, chart):
        """Timing questions ('when', 'is this a good time') need an actual date
        range to narrate, not just a planet/rule name — the bundle previously
        carried only a snapshot (sign, house-from-moon/lagna, retrograde,
        boolean active). This wires `gocharam/timeline.py`'s existing
        ingress/exit boundary walk (already used by `chart.gocharam()` and
        `transits.py`) into the CE bundle rather than reimplementing it.
        `foreign`'s gochara_planets (Rahu, Ketu, Saturn) reliably have at
        least one active rule for this fixture chart, so this is a real
        assertion, not a vacuous "if any" check."""
        as_of = datetime(2026, 8, 9, tzinfo=timezone.utc)
        bundle = assemble_domain(chart, "foreign", include_gochara=True, as_of=as_of)
        active_rules = bundle["gochara"]["active_rules"]
        assert active_rules, "fixture chart should have an active foreign-domain gochara rule"
        saw_a_real_date = False
        for rule in active_rules:
            assert "start_date" in rule and "end_date" in rule
            for key in ("start_date", "end_date"):
                value = rule[key]
                if value is None:
                    continue
                # Must be a genuine, parseable ISO calendar date - not a
                # placeholder string or a boolean/None stand-in.
                parsed = datetime.fromisoformat(value)
                assert 1900 <= parsed.year <= 2100
                saw_a_real_date = True
            if rule["start_date"] and rule["end_date"]:
                assert rule["start_date"] <= rule["end_date"]
        assert saw_a_real_date, "expected at least one real start/end date among active foreign-domain rules"

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

    def test_bare_settle_does_not_misroute_marriage_questions_to_foreign(self):
        """Found during the foreign-domain PR review 2026-08-09: the
        taxonomy's `foreign` keyword list had a bare "settle" entry, which
        matched ordinary marriage-adjacent phrasing ("settle down") with no
        actual foreign-travel content — and since it was the only hit,
        there was no ambiguity signal to trigger clarification. Narrowed
        to "settle abroad"/"settle overseas" in taxonomy.json."""
        decision = KeywordRouter().route("When will I settle down and get married?")
        assert decision.primary != "foreign"
        decision = KeywordRouter().route("Will I settle into a stable routine?")
        assert decision.primary != "foreign"

    @pytest.mark.parametrize("question", [
        "What is my basic personality like?",
        "What are my strengths and weaknesses?",
        "Tell me about my character",
        "What is my temperament according to my chart?",
        "What are my personality traits?",
        "How would you describe my nature?",
        "What's my nature like?",
        "Tell me about my emotional intelligence",
        "What are my blind spots?",
        "What are my biases?",
        "Who am I, really?",
        "I'd like some tips on self improvement",
        "I want more self awareness about myself",
        "Can you tell me about my self-awareness?",
    ])
    def test_personality_questions_route_to_personality(self, question):
        decision = KeywordRouter().route(question)
        assert decision.primary == "personality"

    @pytest.mark.parametrize("question,not_expected", [
        # Regression set: realistic questions from every other domain that
        # must not be pulled toward "personality" by an over-broad keyword —
        # the same category of bug as the "settle abroad"/"settle" collision
        # above. Generic "nature of X" phrasing is the main risk (personality
        # only claims the "my nature" phrase, not bare "nature", for exactly
        # this reason) and "weakness"/"strengths" are scoped to "my
        # weaknesses"/"my strengths" so a literal physical complaint
        # ("weakness in my legs") or an unqualified "financial strengths"
        # phrase can't misroute either.
        ("When will I get a promotion in my job?", "personality"),
        ("Why do I have weakness in my legs?", "personality"),
        ("What is the nature of my illness?", "personality"),
        ("What is the nature of my marriage?", "personality"),
        ("Is this a good year for my marriage?", "personality"),
        ("What is the nature of my spiritual path?", "personality"),
        ("What is the nature of my court case?", "personality"),
        ("What is the nature of my exam results?", "personality"),
        ("What are my financial strengths?", "personality"),
        ("Will I have children soon?", "personality"),
        ("Is this a good time to settle abroad?", "personality"),
    ])
    def test_ordinary_other_domain_questions_do_not_misroute_to_personality(self, question, not_expected):
        decision = KeywordRouter().route(question)
        assert decision.primary != not_expected

    def test_strengths_and_weaknesses_does_not_double_count_as_two_keyword_hits(self):
        """Independent-review finding (round 1, two reviewers independently):
        taxonomy.json originally listed "my strengths", "my weaknesses", AND
        "strengths and weaknesses" as three separate personality keywords.
        The single, most common real phrasing ("what are my strengths and
        weaknesses") matches BOTH "my strengths" and "strengths and
        weaknesses" as literal substrings of the same mention, inflating one
        real signal into 2 keyword hits — KeywordRouter's confidence="high"
        threshold — which, combined with the orchestrator's old
        confidence=="high" clarification bypass, let personality silently
        outrank a genuine one-keyword competitor (career/wealth/children/
        marriage all reproduced) with zero clarification signal. Fixed by
        dropping the redundant "strengths and weaknesses" keyword — "my
        strengths"/"my weaknesses" alone already cover the phrase without
        the self-inflation. Pinned here so it can't silently come back."""
        decision = KeywordRouter().route("What are my strengths and weaknesses?")
        assert decision.matched_terms == ("my strengths",)
        assert decision.confidence == "medium"

    def test_exam_keyword_matches_the_plural_too(self):
        """A second, smaller finding from the same review round: education's
        "exam" keyword is `\\bexam\\b`-matched, which does not match plural
        "exams" — so "competitive exams" (the taxonomy's own description
        text for this domain) scored zero education signal, letting a
        personality-flavored competing phrase ("what are my strengths...for
        competitive exams") win uncontested. Small, obviously-correct fix
        (AGENTS.md Rule 5) alongside the personality-domain change that
        exposed it, not a personality-specific keyword."""
        decision = KeywordRouter().route("How should I prepare for competitive exams?")
        assert "exams" in decision.matched_terms
        assert decision.primary == "education"

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


class TestSourceRetrieverScores:
    """Regression: NaN scores from pgvector broke retrieval, not just JSON.

    A chunk whose embedding is all zeros (the feature-hash embedder produces
    that for text with no Latin words, e.g. Devanagari verses) makes the cosine
    distance undefined. Postgres returns NaN and sorts it as *greater* than
    every real value, so under `order by ... desc` those chunks took the entire
    top of the ranking for every query — and then failed JSON encoding with a
    500 on the way out.
    """

    def test_non_finite_scores_are_clamped_to_zero(self):
        from astrospace.context.source_retriever import _finite

        assert _finite(float("nan")) == 0.0
        assert _finite(float("inf")) == 0.0
        assert _finite(float("-inf")) == 0.0

    def test_ordinary_scores_pass_through(self):
        from astrospace.context.source_retriever import _finite

        assert _finite(0.87) == 0.87
        assert _finite(0) == 0.0
        assert _finite(None) == 0.0
        assert _finite("0.5") == 0.5

    def test_truthiness_guard_would_not_have_caught_nan(self):
        """Documents why `float(value or 0)` was insufficient."""
        nan = float("nan")
        assert bool(nan) is True          # NaN is truthy...
        assert (nan or 0) is nan          # ...so `or 0` never fires
        from astrospace.context.source_retriever import _finite
        assert _finite(nan) == 0.0        # the guard has to test finiteness

    def test_query_guards_the_semantic_term_everywhere_it_appears(self):
        """Both the projected score and the ORDER BY must be guarded.

        Guarding only the projection would fix the 500 while leaving the
        ranking hijacked, which is the more damaging half of the bug.
        """
        import inspect

        from astrospace.context import source_retriever as sr

        sql = inspect.getsource(sr.PostgresSourceRetriever.retrieve)
        assert sql.count("_SEMANTIC") == 2
        assert "nullif" in sr._SEMANTIC and "'NaN'::float8" in sr._SEMANTIC
        # the raw, unguarded expression must not survive anywhere
        assert "(1 - (c.embedding <=>" not in sql
