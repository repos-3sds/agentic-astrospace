"""The deterministic verifier — the only gate before persistence. No model
call in these tests; `verify()` is pure function over a bundle + a
StructuredReading. See astrospace/agents/verifier.py."""
import pytest

from astrospace.agents.schema import Guidance, StructuredReading, TechnicalBasisItem
from astrospace.agents.verifier import verify
from astrospace.context import assemble_domain
from astrospace.core.vedic.chart import VedicChart

DELHI = {"city": "New Delhi", "nation": "IN"}


@pytest.fixture(scope="module")
def marriage_bundle():
    chart = VedicChart("Verifier", 1990, 1, 1, 12, 0, **DELHI)
    return assemble_domain(chart, "marriage")


def _reading(**overrides) -> StructuredReading:
    base = dict(
        acknowledgment="ack",
        technical_basis=[TechnicalBasisItem(factor="7th lord", reading="well placed", source="houses")],
        interpretation="A supportive stretch for partnership matters.",
        summary_and_assurance="A good window, not a fixed outcome.",
        guidance=Guidance(),
        confidence="medium",
    )
    base.update(overrides)
    return StructuredReading(**base)


class TestVerifier:
    def test_clean_reading_passes(self, marriage_bundle):
        assert verify(_reading(), marriage_bundle, "marriage") == []

    def test_invented_citation_fails(self, marriage_bundle):
        bad = _reading(technical_basis=[
            TechnicalBasisItem(factor="x", reading="y", source="totally_invented_ref_id"),
        ])
        violations = verify(bad, marriage_bundle, "marriage")
        assert violations
        assert "totally_invented_ref_id" in violations[0]

    def test_real_reference_id_passes(self, marriage_bundle):
        if not marriage_bundle["references"]:
            pytest.skip("no curated references for this chart/domain combination")
        real_ref_id = marriage_bundle["references"][0]["ref_id"]
        good = _reading(technical_basis=[
            TechnicalBasisItem(factor="x", reading="y", source=real_ref_id),
        ])
        assert verify(good, marriage_bundle, "marriage") == []

    def test_wrong_domain_fails(self, marriage_bundle):
        violations = verify(_reading(), marriage_bundle, "career")
        assert any("does not match routed domain" in v for v in violations)

    @pytest.mark.parametrize("phrase", [
        "you cannot get married because of this dosha",
        "this will end in divorce",
        "your marriage will fail",
        "you will never find a spouse",
        "this dosha means you must not marry",
        "this dosha will destroy your marriage",
    ])
    def test_dosha_fatalism_in_interpretation_fails(self, marriage_bundle, phrase):
        bad = _reading(interpretation=phrase)
        violations = verify(bad, marriage_bundle, "marriage")
        assert any("dosha overclaim" in v for v in violations)

    @pytest.mark.parametrize(("phrase", "kind"), [
        ("you will win your case for sure", "legal"),
        ("you have cancer and should stop your medication", "health"),
    ])
    def test_prohibited_verdict_in_summary_fails(self, marriage_bundle, phrase, kind):
        bad = _reading(summary_and_assurance=phrase)
        violations = verify(bad, marriage_bundle, "marriage")
        assert any(kind in v for v in violations)

    def test_dosha_overclaim_checked_in_technical_basis_too(self, marriage_bundle):
        bad = _reading(technical_basis=[
            TechnicalBasisItem(
                factor="manglik dosha", reading="you cannot marry with this placement",
                source="houses",
            ),
        ])
        violations = verify(bad, marriage_bundle, "marriage")
        assert any("dosha overclaim" in v for v in violations)

    def test_multiple_violations_all_reported(self, marriage_bundle):
        bad = _reading(
            technical_basis=[TechnicalBasisItem(factor="x", reading="y", source="fake_id")],
            interpretation="you will never find a spouse",
        )
        violations = verify(bad, marriage_bundle, "marriage")
        assert len(violations) >= 2
