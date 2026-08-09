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


@pytest.fixture(scope="module")
def wealth_bundle():
    chart = VedicChart("VerifierWealth", 1990, 1, 1, 12, 0, **DELHI)
    return assemble_domain(chart, "wealth")


@pytest.fixture(scope="module")
def children_bundle():
    chart = VedicChart("VerifierChildren", 1990, 1, 1, 12, 0, **DELHI)
    return assemble_domain(chart, "children")


class TestWealthChildrenFatalismAudit:
    """Extends the marriage-fatalism guardrail (`dosha_overclaim_kind()`,
    `astrospace/agents/safety.py`) to wealth and children — an audit gap
    flagged 2026-08-09: the existing `_DOSHA_OVERCLAIM_OUTPUT` patterns are
    all marriage-subject-anchored, so financial and fertility fatalism had
    zero coverage. Confirmed as a real gap (all cases below failed against
    the pre-fix code) before the fix was written, same discipline as PR #7's
    audit and PR #10's regex hardening. The fix generalizes via a windowed
    fatalism-VERB + domain-SUBJECT check (`_domain_fatalism_kind()`) rather
    than a per-sentence list — the same lesson `refer_out_kind()` and
    `_PROHIBITED_OUTPUT`'s clusters already encode."""

    @pytest.mark.parametrize("phrase", [
        "This dosha means you will always struggle financially.",
        "Kemadruma dosha guarantees you will never accumulate wealth.",
        "This yoga dictates permanent poverty for you.",
        "Your finances are cursed by this dosha and will never improve.",
        "This placement condemns you to lifelong financial hardship.",
        "You are doomed to remain poor because of this dosha.",
        "No amount of effort will fix your finances — this dosha seals your fate.",
        "This dosha means your wealth prospects are permanently blocked.",
        "Financial ruin is guaranteed by this yoga.",
        "This dosha forbids you from ever becoming wealthy.",
    ])
    def test_wealth_fatalism_paraphrases_are_caught(self, wealth_bundle, phrase):
        bad = _reading(interpretation=phrase)
        violations = verify(bad, wealth_bundle, "wealth")
        assert violations, f"expected a violation for: {phrase!r}"

    @pytest.mark.parametrize("phrase", [
        "This dosha means you will never have children.",
        "Putra dosha guarantees you will remain childless.",
        "This placement condemns you to a childless life.",
        "You are doomed to never bear children because of this dosha.",
        "This dosha forbids you from ever having a child.",
        "No remedy can undo this — you will never conceive.",
        "This yoga dictates that you will remain without offspring.",
        "Your chances of having children are permanently blocked by this dosha.",
        "Childlessness is guaranteed by this placement.",
        "This dosha seals your fate as childless forever.",
    ])
    def test_children_fatalism_paraphrases_are_caught(self, children_bundle, phrase):
        bad = _reading(interpretation=phrase)
        violations = verify(bad, children_bundle, "children")
        assert violations, f"expected a violation for: {phrase!r}"

    @pytest.mark.parametrize("phrase", [
        # Poetic/metaphorical fatalism — same category, different
        # vocabulary the windowed verb+subject check doesn't cover, so
        # these get their own explicit domain-agnostic patterns (same
        # precedent as "no escaping this fate" already in the file).
        "Divorce is the inevitable outcome.",
        "Your partnership is fated to dissolve.",
        "Poverty is your inescapable destiny.",
        "The cosmos has sentenced you to struggle.",
        "Your womb is cosmically barren.",
        "Birth is blocked by this planetary alignment.",
    ])
    def test_poetic_fatalism_paraphrases_are_caught(self, wealth_bundle, phrase):
        bad = _reading(interpretation=phrase)
        violations = verify(bad, wealth_bundle, "wealth")
        assert violations, f"expected a violation for: {phrase!r}"

    @pytest.mark.parametrize("phrase", [
        # Ordinary, hedged wealth/children guidance that must stay
        # answerable — the regression set proving the fix above doesn't
        # over-trigger on caution language, negated guarantees, or
        # traditional-remedy framing.
        "This dosha does not mean you will never find financial stability — remedies can help.",
        "While this placement can create financial caution, it does not guarantee poverty.",
        "This yoga suggests periods of financial caution, not permanent hardship.",
        "Many people navigate this dosha successfully with careful planning.",
        "This dosha is a flag for financial caution, not a fixed outcome.",
        "Having children later in life is common with this placement.",
        "This dosha may indicate delays in having children, not an inability.",
        "Fertility support and remedies are traditionally recommended for this dosha.",
        "This placement does not prevent you from having children — timing may vary.",
        "Financial growth is supported once this dasha period passes.",
        "This dosha calls for care around joint finances, best paired with a savings habit.",
        "A remedy like this practice is traditionally offered for this dosha, not as a fix but as a support.",
        "Your finances may see some pressure this year, easing after the transit passes.",
        "This dosha is a flag, not a verdict, and traditional remedies can support you.",
        "The 5th house here suggests joy through children later in life, not sooner.",
        "This placement is often read as a caution around expenses, not a permanent condition.",
        "Some classical texts read this as delayed but not denied prosperity.",
        "This yoga rewards patience — financial results tend to arrive later rather than never.",
    ])
    def test_ordinary_wealth_and_children_language_is_not_flagged(self, wealth_bundle, phrase):
        bad = _reading(interpretation=phrase)
        violations = verify(bad, wealth_bundle, "wealth")
        assert violations == [], f"unexpected violation for: {phrase!r}: {violations}"
