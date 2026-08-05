"""Schema contract tests for the Yogas/Doshas knowledge base (US-PR-013).

Every implemented rule must carry: rule id, classical name, category,
source status, implementation status, exact trigger ("rule"), practitioner
explanation, lay explanation, strength rubric, caveats/cancellations, and
source references. This locks that contract in so a future edit to
yogas.json/doshas.json can't silently drop a field the mobile "Learn this
Yoga" sheet (US-PR-014) depends on.
"""
from __future__ import annotations

from astrospace.core.vedic.doshas import dosha_summary
from astrospace.core.vedic.yogas import yoga_summary
from astrospace.knowledge.vedic_rules import get_rule, rules_catalog

REQUIRED_FIELDS = {
    "id", "kind", "name", "category", "rule", "status", "implementation",
    "source_refs", "practitioner_explanation", "lay_explanation",
    "strength_rubric", "caveats", "notes",
}

# design_principles.md §4 — remedies/yogas/doshas never lean on fear or
# guarantee language, even in KB prose that isn't user-facing today.
_BANNED_WORDS = (
    "disaster", "danger", "curse", "doom", "suffer",
    "guaranteed", "will fail", "must buy",
)


class TestRulesCatalogSchema:
    def test_every_rule_has_required_fields(self):
        catalog = rules_catalog()
        assert catalog, "expected a non-empty rules catalog"
        for rule_id, rule in catalog.items():
            missing = REQUIRED_FIELDS - set(rule)
            assert not missing, f"{rule_id} missing fields: {missing}"

    def test_classical_name_and_rule_text_are_non_empty(self):
        for rule_id, rule in rules_catalog().items():
            assert rule["name"], f"{rule_id} missing classical name"
            assert rule["category"], f"{rule_id} missing category"
            assert rule["rule"], f"{rule_id} missing exact trigger text"

    def test_implemented_rules_have_explanations(self):
        """Rules with implementation != not_implemented must explain themselves.

        Pending rules (pitru_dosha, sarpa_dosha) are exempt — they are
        deliberately left thin until a source-backed definition is chosen.
        """
        for rule_id, rule in rules_catalog().items():
            if rule["implementation"] == "not_implemented":
                continue
            assert rule["practitioner_explanation"], f"{rule_id} missing practitioner_explanation"
            assert rule["lay_explanation"], f"{rule_id} missing lay_explanation"
            assert rule["strength_rubric"], f"{rule_id} missing strength_rubric"

    def test_convention_dependent_or_partial_rules_have_caveats(self):
        """A rule that isn't a clean, fully-implemented classical match must
        say why — either in caveats or notes — so the UI has something to
        show for "why is this marked convention-dependent"."""
        for rule_id, rule in rules_catalog().items():
            if rule["status"] == "verified_common" and rule["implementation"] == "computed":
                continue
            assert rule["caveats"] or rule["notes"], (
                f"{rule_id} is {rule['status']}/{rule['implementation']} but has no "
                "caveats or notes explaining the limitation"
            )

    def test_source_refs_point_at_known_sources(self):
        from astrospace.knowledge.vedic_rules.rules import BASE
        import json
        known_sources = set(json.loads((BASE / "sources.json").read_text())["sources"])
        for rule_id, rule in rules_catalog().items():
            for ref in rule["source_refs"]:
                assert ref["source"] in known_sources, (
                    f"{rule_id} cites unknown source {ref['source']!r}"
                )

    def test_get_rule_unknown_id_returns_pending_shape_not_crash(self):
        rule = get_rule("not_a_real_rule")
        assert rule["status"] == "needs_review"
        assert rule["implementation"] == "unknown"
        assert rule["caveats"] == []

    def test_no_fear_or_guarantee_language_in_kb_prose(self):
        for rule_id, rule in rules_catalog().items():
            blob = " ".join([
                rule["practitioner_explanation"], rule["lay_explanation"],
                rule["strength_rubric"], *rule["caveats"], *rule["notes"],
            ]).lower()
            for banned in _BANNED_WORDS:
                assert banned not in blob, f"{rule_id} KB prose leaks fear/guarantee language: {banned}"

    def test_kind_filter_partitions_yogas_and_doshas(self):
        catalog = rules_catalog()
        kinds = {rule["kind"] for rule in catalog.values()}
        assert kinds == {"yoga", "dosha"}


class TestComputedResultsCarryKbFields:
    """Every computed yoga/dosha result is enriched via enrich_rule_result —
    confirm the new fields actually reach the payload a client would see,
    not just the static KB dict."""

    POSITIONS = {
        "Sun": {"lon": 15.0}, "Moon": {"lon": 58.9}, "Mars": {"lon": 70.0},
        "Mercury": {"lon": 98.0}, "Jupiter": {"lon": 140.0}, "Venus": {"lon": 192.0},
        "Saturn": {"lon": 273.0}, "Rahu": {"lon": 185.0}, "Ketu": {"lon": 5.0},
    }
    LAGNA_LON = 10.0

    def test_yoga_results_carry_classical_name_and_explanations(self):
        summary = yoga_summary(self.POSITIONS, self.LAGNA_LON)
        assert summary["all"]
        for result in summary["all"]:
            assert result["classical_name"]
            assert "practitioner_explanation" in result
            assert "lay_explanation" in result
            assert "strength_rubric" in result
            assert "caveats" in result

    def test_dosha_results_carry_classical_name_and_explanations(self):
        summary = dosha_summary(self.POSITIONS, self.LAGNA_LON)
        for result in summary.values():
            assert result["classical_name"]
            assert "practitioner_explanation" in result
            assert "lay_explanation" in result
