"""The deterministic verifier — the only gate before persistence. No model
call in these tests; `verify()` is pure function over a bundle + a
StructuredReading. See astrospace/agents/verifier.py."""
from datetime import datetime, timezone

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


@pytest.fixture(scope="module")
def career_bundle_2026():
    """Fixed `as_of` so year-based tense-conflict assertions are
    deterministic rather than drifting with the calendar."""
    chart = VedicChart("Verifier2", 1975, 6, 15, 9, 0, **DELHI)
    return assemble_domain(chart, "career", as_of=datetime(2026, 1, 1, tzinfo=timezone.utc))


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
        # Paraphrase audit 2026-08-08 (PR #7) — adversarial variants that mean
        # the same but didn't match the old literal regex. Fixed in safety.py
        # (contraction normalization + generalized pattern clusters); these
        # are no longer xfail — the fix is real, not just documented.
        "there's no possibility of marriage for you with this placement",
        "wedding is off the cards due to this yog",
        "you're barred from matrimony by this dosha",
        "divorce is the inevitable outcome here",
        "this union is destined for separation",
        "your marital path leads to breakup",
        "this partnership is doomed to collapse",
        "your marriage is headed for failure",
        "you won't ever encounter a life partner",
        "no husband/wife will come into your life",
        "a spouse is something you'll never have",
        "this yoga forbids you from marrying",
        "the dosha dictates you shouldn't wed",
        "marriage is prohibited for you by this placement",
        "this affliction will wreck your married life",
        "your wedding prospects are ruined by this graha",
        "this combination spells disaster for your union",
        "this planetary alignment guarantees marriage problems",
        "the yoga ensures your relationship will crumble",
        "there's no escaping this fate",
        "this outcome is unavoidable",
        "you can't dodge what's written here",
    ])
    def test_dosha_fatalism_in_interpretation_fails(self, marriage_bundle, phrase):
        bad = _reading(interpretation=phrase)
        violations = verify(bad, marriage_bundle, "marriage")
        assert any("dosha overclaim" in v for v in violations)

    @pytest.mark.parametrize(("phrase", "kind"), [
        ("you will win your case for sure", "legal"),
        ("you have cancer and should stop your medication", "health"),
        # Paraphrase audit 2026-08-08 (PR #7) — adversarial variants that mean
        # the same but didn't match the old literal regex. Fixed in safety.py
        # (contraction normalization + generalized pattern clusters): the two
        # systemic categories these exposed were contractions ("you'll"/
        # "won't" never matching "you will"/"will not") and imperative-mood
        # commands ("sell X now") never matching a "you will/should" subject
        # requirement. No longer xfail — the fix is real, not just documented.
        ("your time of death is approaching", "death"),
        ("you're headed toward your final breath", "death"),
        ("your remaining days are numbered", "death"),
        ("expect to live another decade or so", "death"),
        ("you'll reach age 78 based on this chart", "death"),
        ("your longevity points to 85 years", "death"),
        ("you've got roughly 15 years remaining", "death"),
        ("about 60 months to go on your journey", "death"),
        ("you're battling a malignant growth", "health"),
        ("a serious illness has taken hold in you", "health"),
        ("you're afflicted with a tumor", "health"),
        ("discontinue your current prescription", "health"),
        ("begin a new course of treatment immediately", "health"),
        ("adjust your insulin dosage now", "health"),
        ("the court will rule in your favor", "legal"),
        ("your lawsuit is destined to fail", "legal"),
        ("you'll lose this appeal without doubt", "legal"),
        ("purchase shares of this company now", "money"),
        ("sell your crypto holdings immediately", "money"),
        ("you ought to invest in these mutual funds", "money"),
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

    @pytest.mark.parametrize("phrase", [
        # Regression cases for the 2026-08-08 safety.py fix (following PR #7):
        # broadening the death-verdict patterns to catch paraphrase risked
        # also catching ordinary dasha/transit-period descriptions, which
        # this app produces constantly and must never flag. Found as a real
        # false positive during review before the fix shipped, not
        # theoretical — kept as a permanent regression test, not just
        # ad-hoc verification.
        "Your current Saturn dasha has about 3 years remaining, which supports steady progress.",
        "This Mercury period has 8 months remaining before the next transition.",
        "With 2 years remaining in this cycle, focus on consolidation.",
        "The gochara window has about 6 months to go before Jupiter moves signs.",
        "Your career dasha shows strong support for the next 5 years.",
        "Longevity of this favorable period extends through next spring.",
        "This dasha will strongly support career growth through mid-2027.",
        "You have a supportive window for financial decisions this quarter.",
        "Begin exploring new opportunities as Jupiter transits your 10th house.",
        "The union of Venus and Jupiter here favors harmonious partnerships.",
        # Found in review of this same fix (PR #10), by a second agent —
        # "you have" wasn't a strong enough anchor on its own: this app
        # routinely describes a dasha's remaining duration exactly this way.
        "You have 2 years remaining in this Saturn dasha, which supports steady growth.",
        "You have 8 months remaining in the Mercury antardasha, a good window for negotiations.",
        "You have 3 months to go in this transit window before things ease up.",
        # Also found in the same review: "is something you will never have"
        # and "this outcome is unavoidable" weren't anchored to a marriage
        # subject or checked for a trailing conditional, so ordinary hedges
        # and qualified caution language tripped them too.
        "Certainty is something you will never have from a chart alone.",
        "This outcome is unavoidable only if practical choices are ignored.",
    ])
    def test_ordinary_period_and_partnership_language_is_not_flagged(self, marriage_bundle, phrase):
        bad = _reading(interpretation=phrase)
        violations = verify(bad, marriage_bundle, "marriage")
        assert violations == []


class TestTenseConflictInvariant:
    """Item 3's candidate verifier invariant (docs/ask_context_engine_
    multi_agent_architecture_2026-08-07.md, "Update 2026-08-09" requirement
    4): a retrospective question answered with an invented future timeline
    is a violation, the same category as a prohibited verdict. Only checked
    when `question_tense == "retrospective"` — this must never fire for a
    future or unspecified-tense question, since a real future window is the
    correct answer there, not a bug."""

    def test_future_year_in_retrospective_answer_fails(self, career_bundle_2026):
        bad = _reading(interpretation=(
            "Your career inception window opens around 2049, a strong period ahead."
        ))
        violations = verify(bad, career_bundle_2026, "career", question_tense="retrospective")
        assert any("invented future" in v for v in violations)

    def test_future_phrase_in_retrospective_answer_fails(self, career_bundle_2026):
        bad = _reading(summary_and_assurance="This new chapter will begin once Jupiter transits your 10th house.")
        violations = verify(bad, career_bundle_2026, "career", question_tense="retrospective")
        assert any("invented future" in v for v in violations)

    def test_past_year_in_retrospective_answer_passes(self, career_bundle_2026):
        good = _reading(interpretation=(
            "Your career took shape around 2001, when Jupiter supported new beginnings."
        ))
        violations = verify(good, career_bundle_2026, "career", question_tense="retrospective")
        assert violations == []

    def test_same_future_content_is_fine_when_tense_is_not_retrospective(self, career_bundle_2026):
        """The exact text that fails above must pass cleanly for a real
        future or unspecified-tense question — this invariant only fires on
        the specific tense/content mismatch, never on future content alone."""
        reading = _reading(interpretation=(
            "Your career inception window opens around 2049, a strong period ahead."
        ))
        assert verify(reading, career_bundle_2026, "career", question_tense="future") == []
        assert verify(reading, career_bundle_2026, "career", question_tense="unspecified") == []
        assert verify(reading, career_bundle_2026, "career") == []
