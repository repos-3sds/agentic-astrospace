"""The deterministic verifier — the only gate before persistence. No model
call in these tests; `verify()` is pure function over a bundle + a
StructuredReading. See astrospace/agents/verifier.py."""
from datetime import datetime, timezone

import pytest

from astrospace.agents.schema import Guidance, RemedyItem, StructuredReading, TechnicalBasisItem
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
    audit and PR #10's regex hardening.

    History worth reading before touching this: the first two fix attempts
    used a *generic* mechanism (any of a dozen "fatalism verbs" matched
    against any of a handful of "domain subject" words within a window or a
    clause). Three independent review rounds each found real bugs in that
    approach — no negation handling, then a negation window wide enough to
    swallow unrelated negations and disqualify real violations, a clause
    splitter that didn't handle colons/em-dashes/parens, a verb pattern that
    permanently disqualified itself, and a `\\b`-missing regex that matched
    "certain" inside "uncertain". The explicit marriage patterns above, and
    the explicit poetic patterns in `_DOSHA_OVERCLAIM_OUTPUT`, were reviewed
    clean across all three rounds. So this is now explicit phrase matching
    (same style as marriage), plus one shared, narrowly-scoped, backward-
    looking `_negation_precedes()` check applied to the whole list —
    documented in `safety.py` itself, tested here from every angle that
    broke a previous version."""

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

    @pytest.mark.parametrize("phrase", [
        # Found by independent review of the first version of this fix: a
        # flat character-window with per-pattern lookbehinds only on
        # "guarantee" had no negation handling for "will never"/"will
        # always" at all, so the canonical flag-not-verdict sentence
        # CLAUDE.md requires was itself flagged as an overclaim.
        "This dosha does not mean you will never have children.",
        "It does not mean you will always struggle financially — remedies help.",
        "This placement does not mean you are doomed to remain poor.",
        "This yoga guarantees nothing about your finances.",
        "No chart guarantees poverty or wealth; effort matters.",
        "It is a myth that this dosha condemns you to childlessness; classical texts disagree.",
        "This dosha does not forbid you from ever having children.",
        "Wealth is never guaranteed by this dosha, only supported.",
        "By no means is this dosha a guarantee of poverty.",
        "It does not, in any reading, guarantee poverty.",
    ])
    def test_negated_reassurance_is_not_flagged(self, wealth_bundle, phrase):
        bad = _reading(interpretation=phrase)
        violations = verify(bad, wealth_bundle, "wealth")
        assert violations == [], f"unexpected violation for: {phrase!r}: {violations}"

    @pytest.mark.parametrize("phrase", [
        # Found by independent review: a flat ±45-char window doesn't
        # respect clause boundaries, so a fatalism verb and a domain
        # subject in unrelated clauses of the same sentence were flagged
        # as if they were connected.
        "The 2nd house governs your finances; a single dosha will always be one factor among many.",
        "This dasha supports having children later; the chart will never fix a date for you.",
        "Traditional remedies for your finances exist, though no remedy can undo this dasha's timing.",
    ])
    def test_unrelated_clauses_are_not_flagged(self, wealth_bundle, phrase):
        bad = _reading(interpretation=phrase)
        violations = verify(bad, wealth_bundle, "wealth")
        assert violations == [], f"unexpected violation for: {phrase!r}: {violations}"

    @pytest.mark.parametrize("phrase", [
        "You are destined for poverty because of this dosha.",
        "You are destined to remain childless.",
        "This dosha ensures you will remain childless.",
        "This yoga makes poverty certain for you.",
    ])
    def test_additional_fatalism_phrasings_are_caught(self, wealth_bundle, phrase):
        """A few more direct paraphrases found by review, added once the
        negation/clause fixes above made it safe to widen the verb list."""
        bad = _reading(interpretation=phrase)
        violations = verify(bad, wealth_bundle, "wealth")
        assert violations, f"expected a violation for: {phrase!r}"

    @pytest.mark.parametrize("phrase", [
        # A THIRD independent review found the clause/negation-window fix
        # above still had real bugs: an unrelated, earlier negation in a
        # compound or multi-sentence answer disqualified a real, later,
        # unnegated fatalism claim (the exact opposite failure mode from
        # what it was fixing). Sentence-scoped now — a negation in a
        # previous sentence (bounded by . ; :) must not reach forward.
        "Your chart does not lie: this dosha guarantees poverty.",
        "This is not a small matter. You are destined for poverty.",
        "Remedies cannot help here. This yoga guarantees childlessness.",
        "There is not a single mitigating factor. You will always struggle financially.",
        "I will not soften this. You will never have children because of this yoga.",
        "It is not a matter of effort. Poverty is guaranteed by this yoga.",
        "Do not hope for improvement: this placement seals your fate of poverty.",
    ])
    def test_unrelated_earlier_negation_does_not_suppress_a_real_violation(self, wealth_bundle, phrase):
        bad = _reading(interpretation=phrase)
        violations = verify(bad, wealth_bundle, "wealth")
        assert violations, f"expected a violation for: {phrase!r}"

    def test_a_verb_pattern_cannot_permanently_disqualify_itself(self, wealth_bundle):
        """The same review found `cannot be undone` unreachable: `cannot`
        was both the verb's own trigger word and a negation cue, so the
        negation check always found its own match and skipped every case.
        Same root cause as the case above, this is the sharpest version of
        it — the negation source and the violation are the identical word."""
        bad = _reading(interpretation="This dosha cannot be undone and poverty will follow.")
        violations = verify(bad, wealth_bundle, "wealth")
        assert violations, "the verb's own text must not disqualify its own match"

    @pytest.mark.parametrize("phrase", [
        # More negation forms the third review demonstrated the previous
        # cue list missed outright — debunking language ("misconception",
        # "wrongly claim") is the sharpest case: the app would flag itself
        # for correcting a superstition.
        "Financial ruin is never guaranteed by a single placement.",
        "It is a misconception that this dosha guarantees poverty.",
        "Some astrologers wrongly claim this dosha guarantees childlessness.",
        "No astrologer should ever tell you that you will never have children.",
        "Ignore any reading that claims you will always struggle financially.",
        "It is false that this placement guarantees poverty.",
        "This dosha never means you will never have children.",
        "It is not true that this dosha, which the classical texts discuss "
        "at some length, guarantees poverty.",
    ])
    def test_additional_negation_forms_are_not_flagged(self, wealth_bundle, phrase):
        bad = _reading(interpretation=phrase)
        violations = verify(bad, wealth_bundle, "wealth")
        assert violations == [], f"unexpected violation for: {phrase!r}: {violations}"

    @pytest.mark.parametrize("phrase", [
        # The third review's cross-clause collision corpus using boundary
        # characters the previous clause-splitter didn't handle: colon,
        # em-dash, "but"/"though" without a comma, and parentheses.
        "The 2nd house governs your finances: a single dosha will always be one factor among many.",
        "The 2nd house governs your finances — a single dosha will always be one factor among many.",
        "The 5th house shows chances of having children but a chart will never be the whole story.",
        "Saturn shapes your finances though effort will always matter more.",
        "Let us look at your finances (a dosha will never be the only factor here).",
    ])
    def test_more_cross_clause_collisions_are_not_flagged(self, wealth_bundle, phrase):
        bad = _reading(interpretation=phrase)
        violations = verify(bad, wealth_bundle, "wealth")
        assert violations == [], f"unexpected violation for: {phrase!r}: {violations}"

    @pytest.mark.parametrize("phrase", [
        # The third review showed the generic verbs added in round 2
        # (ensures, destined to, will always) misfired on exactly the kind
        # of sentence `guidance.practical_actions`/`remedies` produce —
        # direct evidence for abandoning the generic verb list in favor of
        # explicit phrases, which don't have this failure mode because they
        # require the fatalistic complement, not just the bare verb.
        "Careful planning ensures your finances recover after this transit.",
        "A written budget ensures your finances stay under control.",
        "Regular charity ensures your finances get steady attention.",
        "Your finances will always benefit from a written budget.",
        "Couples destined to meet often ask about having children early.",
        "Consulting a fertility specialist ensures having children stays a medical conversation.",
        "This placement makes your finances uncertain for a while.",
        # This one demonstrates the actual regex bug found: a missing `\b`
        # before "certain" let the pattern match "certain" *inside*
        # "uncertain", inverting the meaning of a direct CLAUDE.md
        # non-negotiable statement into a flagged violation.
        "Nothing in a chart makes having children certain or impossible.",
    ])
    def test_benign_action_and_remedy_style_sentences_are_not_flagged(self, wealth_bundle, phrase):
        bad = _reading(interpretation=phrase)
        violations = verify(bad, wealth_bundle, "wealth")
        assert violations == [], f"unexpected violation for: {phrase!r}: {violations}"

    @pytest.mark.parametrize("phrase", [
        # Bonus: the third review found this exact class of bug was
        # already live in the untouched marriage patterns on `main` — the
        # shared `_negation_precedes()` check fixes it for free, since it
        # now runs across the whole `_DOSHA_OVERCLAIM_OUTPUT` list, not
        # just the wealth/children additions.
        "This dosha does not mean you will never find a spouse.",
        "A manglik dosha does not mean you cannot marry.",
    ])
    def test_marriage_negation_bug_fixed_as_a_side_effect(self, marriage_bundle, phrase):
        bad = _reading(interpretation=phrase)
        violations = verify(bad, marriage_bundle, "marriage")
        assert violations == [], f"unexpected violation for: {phrase!r}: {violations}"


class TestFullFieldCoverage:
    """Found by a second independent review of PR #12: `text_to_check` had
    only ever covered `interpretation`/`summary_and_assurance` (plus,
    after the first review fix, `technical_basis`/`practical_actions`) —
    `acknowledgment`, `guidance.remedies[].practice`, `guidance.remedies[].note`,
    and `guidance.follow_up_questions` were never scanned by ANY check here,
    not just the tense one. Demonstrated as a real gap: a prohibited death
    verdict placed in a remedy note passed cleanly before this fix. That's
    CLAUDE.md non-negotiable #1 (no death/longevity verdicts) landing in a
    field nothing was looking at — this is the regression test for exactly
    that, not a hypothetical."""

    def test_prohibited_verdict_in_remedy_note_fails(self, marriage_bundle):
        bad = _reading(guidance=Guidance(remedies=[
            RemedyItem(practice="a traditional practice", note="You will die in 2049."),
        ]))
        violations = verify(bad, marriage_bundle, "marriage")
        assert any("prohibited verdict" in v for v in violations)

    def test_prohibited_verdict_in_remedy_practice_fails(self, marriage_bundle):
        bad = _reading(guidance=Guidance(remedies=[
            RemedyItem(practice="You will die in 2049.", note="context"),
        ]))
        violations = verify(bad, marriage_bundle, "marriage")
        assert any("prohibited verdict" in v for v in violations)

    def test_prohibited_verdict_in_follow_up_question_fails(self, marriage_bundle):
        bad = _reading(guidance=Guidance(follow_up_questions=["You will die in 2049."]))
        violations = verify(bad, marriage_bundle, "marriage")
        assert any("prohibited verdict" in v for v in violations)

    def test_prohibited_verdict_in_acknowledgment_fails(self, marriage_bundle):
        bad = _reading(acknowledgment="You will die in 2049.")
        violations = verify(bad, marriage_bundle, "marriage")
        assert any("prohibited verdict" in v for v in violations)

    def test_clean_remedies_and_follow_ups_pass(self, marriage_bundle):
        good = _reading(guidance=Guidance(
            remedies=[RemedyItem(practice="A traditional practice, offered helpfully.",
                                 note="Traditionally associated with this placement.")],
            follow_up_questions=["Which month is strongest for this?"],
        ))
        assert verify(good, marriage_bundle, "marriage") == []


class TestTenseConflictInvariant:
    """Item 3's candidate verifier invariant (docs/ask_context_engine_
    multi_agent_architecture_2026-08-07.md, "Update 2026-08-09" requirement
    4): a retrospective question answered with an invented future timeline
    is a violation, the same category as a prohibited verdict. Only checked
    when `question_tense == "retrospective"` — this must never fire for a
    future, mixed, or unspecified-tense question, since a real future
    window is the correct answer there, not a bug.

    Revised after independent review of the first version of this PR, which
    had a real false-positive: any 4-digit year past `as_of` was flagged,
    including the bundle's own dasha period boundaries — the currently
    running mahadasha always ends in the future, and the prompt tells the
    model to cite exactly that. `career_bundle_2026`'s real mahadasha (Rahu,
    2020->2038) is used directly below rather than an assumed one, so this
    test is checked against what the bundle actually contains, not a guess.
    The old phrase-based check ("will begin"/"upcoming") is gone entirely —
    it flagged ordinary constructive closes, including ones explicitly
    rejecting a future framing; the year check is the precise signal that
    matches the actual reported bug."""

    def test_future_year_in_retrospective_answer_fails(self, career_bundle_2026):
        bad = _reading(interpretation=(
            "Your career inception window opens around 2049, a strong period ahead."
        ))
        violations = verify(bad, career_bundle_2026, "career", question_tense="retrospective")
        assert any("invented future" in v for v in violations)

    def test_real_dasha_period_boundary_is_not_flagged(self, career_bundle_2026):
        boundary_end = career_bundle_2026["dasha_relevance"]["chain"][0]["end"][:4]
        good = _reading(interpretation=(
            f"Your career move in 2021 fell inside the Rahu mahadasha, which runs "
            f"2020 to {boundary_end}."
        ))
        violations = verify(good, career_bundle_2026, "career", question_tense="retrospective")
        assert violations == []

    def test_ordinary_constructive_close_with_will_begin_is_not_flagged(self, career_bundle_2026):
        """The exact phrasing that used to trip the removed phrase-based
        check — an ordinary, non-timeline-inventing close."""
        good = _reading(summary_and_assurance=(
            "That chapter is complete; a quieter phase will begin as you settle in."
        ))
        violations = verify(good, career_bundle_2026, "career", question_tense="retrospective")
        assert violations == []

    def test_fabricated_year_in_technical_basis_is_caught(self, career_bundle_2026):
        bad = _reading(technical_basis=[
            TechnicalBasisItem(factor="x", reading="Career inception window opens 2049.", source="houses"),
        ])
        violations = verify(bad, career_bundle_2026, "career", question_tense="retrospective")
        assert any("invented future" in v for v in violations)

    def test_fabricated_year_in_practical_actions_is_caught(self, career_bundle_2026):
        bad = _reading(guidance=Guidance(practical_actions=["Prepare for your career start in 2049."]))
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
        future, mixed, or unspecified-tense question — this invariant only
        fires on the specific tense/content mismatch, never on future
        content alone."""
        reading = _reading(interpretation=(
            "Your career inception window opens around 2049, a strong period ahead."
        ))
        assert verify(reading, career_bundle_2026, "career", question_tense="future") == []
        assert verify(reading, career_bundle_2026, "career", question_tense="mixed") == []
        assert verify(reading, career_bundle_2026, "career", question_tense="unspecified") == []
        assert verify(reading, career_bundle_2026, "career") == []

    def test_profile_facts_is_a_valid_technical_basis_source(self, career_bundle_2026):
        """profile_facts is a real bundle section (added by this PR) — a
        model citing it as a source must not get a spurious invalid-source
        violation, the same as any other bundle section name."""
        reading = _reading(technical_basis=[
            TechnicalBasisItem(factor="age", reading="You are 51.", source="profile_facts"),
        ])
        assert verify(reading, career_bundle_2026, "career") == []
