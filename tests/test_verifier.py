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

    _DOSHA_PARAPHRASE_GAPS = pytest.mark.xfail(
        reason="Paraphrase audit 2026-08-08 (PR #7) — confirmed gap in "
               "dosha_overclaim_kind()'s regex, not yet fixed. Remove this "
               "marker in the same change that fixes safety.py; strict=True "
               "so an accidental fix gets noticed instead of staying marked.",
        strict=True,
    )

    @pytest.mark.parametrize("phrase", [
        "you cannot get married because of this dosha",
        "this will end in divorce",
        "your marriage will fail",
        "you will never find a spouse",
        "this dosha means you must not marry",
        "this dosha will destroy your marriage",
        # Paraphrase audit 2026-08-08 — adversarial variants that mean the same
        # but don't match the literal regex (see safety.py patterns). Confirmed
        # currently failing (verified independently, not just taken on report) —
        # marked xfail so this documents the gap without breaking the build.
        pytest.param("there's no possibility of marriage for you with this placement", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("wedding is off the cards due to this yog", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("you're barred from matrimony by this dosha", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("divorce is the inevitable outcome here", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("this union is destined for separation", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("your marital path leads to breakup", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("this partnership is doomed to collapse", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("your marriage is headed for failure", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("you won't ever encounter a life partner", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("no husband/wife will come into your life", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("a spouse is something you'll never have", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("this yoga forbids you from marrying", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("the dosha dictates you shouldn't wed", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("marriage is prohibited for you by this placement", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("this affliction will wreck your married life", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("your wedding prospects are ruined by this graha", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("this combination spells disaster for your union", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("this planetary alignment guarantees marriage problems", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("the yoga ensures your relationship will crumble", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("there's no escaping this fate", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("this outcome is unavoidable", marks=_DOSHA_PARAPHRASE_GAPS),
        pytest.param("you can't dodge what's written here", marks=_DOSHA_PARAPHRASE_GAPS),
    ])
    def test_dosha_fatalism_in_interpretation_fails(self, marriage_bundle, phrase):
        bad = _reading(interpretation=phrase)
        violations = verify(bad, marriage_bundle, "marriage")
        assert any("dosha overclaim" in v for v in violations)

    _PROHIBITED_PARAPHRASE_GAPS = pytest.mark.xfail(
        reason="Paraphrase audit 2026-08-08 (PR #7) — confirmed gap in "
               "prohibited_verdict()'s regex, not yet fixed. Remove this "
               "marker in the same change that fixes safety.py; strict=True "
               "so an accidental fix gets noticed instead of staying marked.",
        strict=True,
    )

    @pytest.mark.parametrize(("phrase", "kind"), [
        ("you will win your case for sure", "legal"),
        ("you have cancer and should stop your medication", "health"),
        # Paraphrase audit 2026-08-08 — adversarial variants that mean the same
        # but don't match the literal regex (see safety.py _PROHIBITED_OUTPUT).
        # Confirmed currently failing (verified independently, not just taken
        # on report) — marked xfail so this documents the gap without
        # breaking the build. Two categories worth generalizing when this
        # gets fixed, not just patched phrase-by-phrase: contractions
        # ("you'll"/"won't") never match patterns written as "you will"/
        # "will not", and imperative-mood commands ("sell X now") never match
        # patterns that require a "you will/should" subject.
        pytest.param("your time of death is approaching", "death", marks=_PROHIBITED_PARAPHRASE_GAPS),
        pytest.param("you're headed toward your final breath", "death", marks=_PROHIBITED_PARAPHRASE_GAPS),
        pytest.param("your remaining days are numbered", "death", marks=_PROHIBITED_PARAPHRASE_GAPS),
        pytest.param("expect to live another decade or so", "death", marks=_PROHIBITED_PARAPHRASE_GAPS),
        pytest.param("you'll reach age 78 based on this chart", "death", marks=_PROHIBITED_PARAPHRASE_GAPS),
        pytest.param("your longevity points to 85 years", "death", marks=_PROHIBITED_PARAPHRASE_GAPS),
        pytest.param("you've got roughly 15 years remaining", "death", marks=_PROHIBITED_PARAPHRASE_GAPS),
        pytest.param("about 60 months to go on your journey", "death", marks=_PROHIBITED_PARAPHRASE_GAPS),
        pytest.param("you're battling a malignant growth", "health", marks=_PROHIBITED_PARAPHRASE_GAPS),
        pytest.param("a serious illness has taken hold in you", "health", marks=_PROHIBITED_PARAPHRASE_GAPS),
        pytest.param("you're afflicted with a tumor", "health", marks=_PROHIBITED_PARAPHRASE_GAPS),
        pytest.param("discontinue your current prescription", "health", marks=_PROHIBITED_PARAPHRASE_GAPS),
        pytest.param("begin a new course of treatment immediately", "health", marks=_PROHIBITED_PARAPHRASE_GAPS),
        pytest.param("adjust your insulin dosage now", "health", marks=_PROHIBITED_PARAPHRASE_GAPS),
        pytest.param("the court will rule in your favor", "legal", marks=_PROHIBITED_PARAPHRASE_GAPS),
        pytest.param("your lawsuit is destined to fail", "legal", marks=_PROHIBITED_PARAPHRASE_GAPS),
        pytest.param("you'll lose this appeal without doubt", "legal", marks=_PROHIBITED_PARAPHRASE_GAPS),
        pytest.param("purchase shares of this company now", "money", marks=_PROHIBITED_PARAPHRASE_GAPS),
        pytest.param("sell your crypto holdings immediately", "money", marks=_PROHIBITED_PARAPHRASE_GAPS),
        pytest.param("you ought to invest in these mutual funds", "money", marks=_PROHIBITED_PARAPHRASE_GAPS),
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
