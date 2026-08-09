"""Refer-out safety gate — shared by every agent surface (Ask, domain
agents, and any future one).

Deliberately not agent-owned: distributing this into each domain agent's
own prompt/logic is how the boundary drifts out of sync between them. It
wraps the orchestrator once, before any model call, and again on the way
out.
"""
import re

# Contraction expansion, applied before every pattern in this module sees
# normalized text. "you'll"/"won't"/"can't"/"you're" etc. never matched a
# single one of the patterns below that were written in full form ("you
# will"/"will not"/"cannot"/"you are") — confirmed as a real, systemic gap by
# the 2026-08-08 paraphrase audit (PR #7): most of its 44 confirmed cases
# used a contraction specifically because the full form was already covered.
# Normalizing once here means every pattern below can be written in full
# form without an apostrophe-variant for each one.
_CONTRACTIONS = (
    (r"\byou'll\b", "you will"), (r"\byou're\b", "you are"),
    (r"\byou've\b", "you have"), (r"\bwon't\b", "will not"),
    (r"\bcan't\b", "cannot"), (r"\bdon't\b", "do not"),
    (r"\bdoesn't\b", "does not"), (r"\bshouldn't\b", "should not"),
    (r"\bisn't\b", "is not"), (r"\bit's\b", "it is"),
    (r"\bthere's\b", "there is"), (r"\bwhat's\b", "what is"),
    (r"\bwe've\b", "we have"), (r"\bi've\b", "i have"),
)


def _normalize(text: str) -> str:
    normalized = " ".join(text.casefold().split())
    for pattern, expansion in _CONTRACTIONS:
        normalized = re.sub(pattern, expansion, normalized)
    return normalized


# Refer-out matching is deliberately two-part: a prohibited SUBJECT plus a
# VERDICT-SEEKING frame. Matching whole phrasings — the previous approach — let
# 24 of 31 probe questions through, because an allowlist of sentences cannot
# cover paraphrase. "when will i die" was caught; "how many years do i have
# left" was not.
#
# The two-part rule is also what keeps ordinary questions answerable. The app's
# own suggested prompt is "Is this month good for a big purchase?" — money
# subject, timing frame, no verdict sought — and the refer-out screen explicitly
# offers timing for decisions already made. Subject alone must never gate.

_VERDICT_FRAMES = (
    r"\bwill\b", r"\bwhen will\b", r"\bhow long\b", r"\bhow many\b",
    r"\bwhat is my\b", r"\bwhat are my\b", r"\bdo i have\b", r"\bam i\b",
    r"\bshould i\b", r"\bcan i\b", r"\bis it going to\b", r"\bgoing to\b",
    r"\bpredict\b", r"\btell me\b", r"\bcalculate\b", r"\bchances? of\b",
    r"\blikelihood\b", r"\bwhat will\b", r"\bwhen do i\b", r"\bhave left\b",
    r"\bdiagnos", r"\bwhat does .{0,20}mean for my\b",
)

# Subjects the app must never issue a verdict on. Kept as word-stems so
# inflections ("survive"/"survival") are covered without listing each form.
_REFER_OUT_SUBJECTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("death", (
        r"\bdie\b", r"\bdeath\b", r"\bdying\b", r"\bdead\b",
        r"\blifespan\b", r"\blongevity\b", r"\blife expectancy\b",
        r"\bsurviv", r"\bpass away\b", r"\byears (?:do i|i) have\b",
        r"\bhow long .{0,20}\blive\b", r"\bkill", r"\bfatal\b", r"\bterminal\b",
        # Devanagari and Telugu death terms. NOT a substitute for review by a
        # fluent speaker — see docs; these cover the literal words only.
        r"मृत्यु", r"मौत", r"मरण", r"మరణ", r"చనిపో",
    )),
    ("health", (
        r"\bdiagnos", r"\bmedical advice\b", r"\btreatment plan\b",
        r"\bdisease\b", r"\bcancer\b", r"\bchemo", r"\btumou?r\b",
        r"\billness\b", r"\bsick\b", r"\bsymptom", r"\bmedicine\b",
        r"\bmedication\b", r"\binsulin\b", r"\bdose\b", r"\bdosage\b",
        r"\bsurgery\b", r"\boperation\b", r"\brecover\b", r"\brecovery\b",
        r"\bcure\b", r"\bcured\b", r"\bpregnan", r"\bmiscarriage\b",
        r"\bdepress", r"\bsuicid", r"\bmental (?:health|illness)\b",
        r"बीमारी", r"అనారోగ్య", r"వ్యాధి",
    )),
    ("legal", (
        r"\blegal advice\b", r"\bsue\b", r"\blawsuit\b", r"\bcourt\b",
        r"\bjudge\b", r"\bjury\b", r"\bverdict\b", r"\bprison\b",
        r"\bjail\b", r"\bconvict", r"\bacquit", r"\bguilty\b",
        r"\bcase\b.{0,20}\b(?:win|lose|outcome)\b", r"\bbail\b",
        r"\bcustody\b", r"\bdivorce settlement\b", r"\bvisa\b.{0,16}\b(?:approved|rejected)\b",
    )),
    ("money", (
        # Directive-seeking only. "Is this month good to buy property" is a
        # timing question and stays answerable — see the note above.
        r"\b(?:stock|share|crypto|coin|mutual fund|bitcoin)\b",
        r"\bshould i (?:buy|sell|invest|trade)\b",
        r"\bwhich .{0,16}\b(?:invest|fund|stock)\b",
        r"\bmarket\b.{0,24}\b(?:rise|fall|crash|go up|go down)\b",
        r"\bguaranteed (?:return|profit)\b", r"\brisk[- ]free\b",
        r"\bwill i (?:become|be) rich\b", r"\bhow much money will\b",
    )),
)

REFER_OUT_ANSWERS = {
    "death": "AstroSpace does not predict death or lifespan, for anyone.",
    "health": "AstroSpace cannot diagnose illness, predict medical outcomes, or recommend treatment. Please consult a qualified medical professional.",
    "legal": "AstroSpace cannot predict legal outcomes or provide legal advice. Please consult a qualified legal professional.",
    "money": "AstroSpace cannot recommend investments or predict markets. Please consult a qualified financial professional.",
}


def refer_out_kind(question: str) -> str | None:
    """Return a structured safety boundary before any model is invoked.

    A question is referred out when it names a prohibited SUBJECT *and* seeks a
    VERDICT about it. Both halves are required: "is this month good for a big
    purchase?" names money but asks about timing, and the product explicitly
    answers that. "which stock should i buy?" seeks a directive and does not.

    Death is the exception — it is gated on subject alone. There is no framing
    in which the app answers a question about when someone dies, so requiring a
    verdict frame would only create a gap to phrase around.
    """
    normalized = _normalize(question)
    seeks_verdict = any(re.search(f, normalized) for f in _VERDICT_FRAMES)
    for kind, subjects in _REFER_OUT_SUBJECTS:
        if not any(re.search(pattern, normalized) for pattern in subjects):
            continue
        if kind == "death" or seeks_verdict:
            return kind
    return None


# Output-side net. The input gate cannot catch every phrasing in every language,
# and nothing previously checked what the model actually said — so a longevity
# verdict produced anyway would have been returned verbatim. This is the second
# layer, and it is why the input rules can stay conservative about false
# positives: the boundary does not rest on them alone.
#
# 2026-08-08 (PR #7 paraphrase audit, fixed here): the original flat
# phrase-list had the exact weakness refer_out_kind() used to have before its
# own two-part redesign — 20 of 20 audited paraphrases slipped through
# because each pattern only matched its own wording. The additions below are
# generalized clusters (verb/noun alternations, gap-tolerant word order),
# not copies of the audit's specific sentences — a real fix generalizes past
# the exact cases that exposed the gap, or the next paraphrase finds it again.
_PROHIBITED_OUTPUT = (
    (r"\byou (?:will|are going to) die\b", "death"),
    (r"\byour (?:time of )?(?:death|dying|lifespan|life expectancy|longevity)\b", "death"),
    (r"\byou (?:will|are likely to) live (?:until|to|for)\b", "death"),
    (r"\byou have\b.{0,24}\b(?:years|months) (?:left|to live)\b", "death"),
    (r"\b\d+\s*months? to go on your journey\b", "death"),
    (r"\breach age \d+\b", "death"),
    (r"\bheaded toward (?:your )?(?:final|last) breath\b", "death"),
    (r"\b(?:remaining )?days are numbered\b", "death"),
    (r"\bexpect to live (?:another|for)\b.{0,20}\b(?:decade|year|month)s?\b", "death"),
    (r"\byou (?:have|are suffering from)\b.{0,24}\b(?:cancer|disease|tumou?r)\b", "health"),
    (r"\b(?:battling|suffering from|afflicted with)\b.{0,20}\b(?:malignant growth|tumou?r|cancer)\b", "health"),
    (r"\billness has taken hold\b", "health"),
    (r"\b(?:stop|start|change|discontinue|adjust|begin)\b.{0,32}\b(?:medication|medicine|insulin|prescription|dosage|dose|treatment)\b", "health"),
    (r"\byou will (?:win|lose) (?:the|your|this) (?:case|lawsuit|appeal)\b", "legal"),
    (r"\b(?:court|judge) will rule in your favor\b", "legal"),
    (r"\b(?:lawsuit|case|appeal) is destined to fail\b", "legal"),
    (r"\byou (?:will|should|ought to) (?:buy|sell|invest in|purchase)\b.{0,24}\b(?:stock|share|crypto|mutual funds?)\b", "money"),
    (r"\b(?:purchase|buy|sell|invest in)\b.{0,20}\b(?:stocks?|shares?|crypto|holdings|mutual funds?)\b.{0,25}\b(?:now|immediately|today)\b", "money"),
)


# "N years/months remaining" needs its own function, not a line in
# _PROHIBITED_OUTPUT: whether it's a death verdict or an ordinary,
# constantly-produced dasha/transit-period description ("you have 2 years
# remaining in this Saturn dasha") depends on whether an astrological
# period noun appears *anywhere* nearby — before or after the number. A
# single regex can't express that in Python's `re` module (no
# variable-length lookbehind), and anchoring only to "you have" isn't
# enough either — that phrasing is exactly how this app describes a
# dasha's remaining duration too. Found as a real false positive twice:
# once during initial review ("this Saturn dasha has 3 years remaining"),
# once again in review by another agent ("you have 2 years remaining in
# this Saturn dasha") — the second case is why this moved out of a plain
# regex line into a windowed context check.
_PERIOD_NOUNS = re.compile(
    r"\b(?:dasha|antardasha|pratyantardasha|sookshma|period|transit|"
    r"cycle|phase|window)\b"
)
_YEARS_MONTHS_REMAINING = re.compile(
    r"\byou have\b.{0,20}\b\d+\s*(?:years?|months?)\s*(?:remaining|left|to go)\b"
)


def _personal_years_remaining(normalized: str) -> bool:
    for match in _YEARS_MONTHS_REMAINING.finditer(normalized):
        window = normalized[max(0, match.start() - 40):match.end() + 40]
        if not _PERIOD_NOUNS.search(window):
            return True
    return False


def prohibited_verdict(answer: str) -> str | None:
    """Which boundary an answer crosses, if any. None means it is clean."""
    normalized = _normalize(answer)
    if _personal_years_remaining(normalized):
        return "death"
    for pattern, kind in _PROHIBITED_OUTPUT:
        if re.search(pattern, normalized):
            return kind
    return None


# "A dosha is a flag, not a verdict" (CLAUDE.md, non-negotiable) had only a
# prompt instruction, no net — unlike refer-out's input+output pair. Written
# marriage-first: manglik/gandanta/grahan dosha is exactly where this fails
# if it's weak, and marriage is the first sensitive domain shipping with it.
#
# 2026-08-08 (PR #7 paraphrase audit, fixed here): same generalization
# principle as _PROHIBITED_OUTPUT above — clusters, not copied sentences.
_DOSHA_OVERCLAIM_OUTPUT = (
    r"\byou cannot (?:get married|marry)\b",
    r"\b(?:will|is going to) end in divorce\b",
    r"\bmarriage will fail\b",
    r"\byou will never (?:find|get) a (?:spouse|partner|husband|wife)\b",
    r"\bdosha means you (?:must not|cannot|should never) marry\b",
    r"\bthis dosha will (?:destroy|ruin) your marriage\b",
    r"\b(?:dosha|yoga) (?:will definitely|definitely will|will certainly) cause\b",
    r"\bcannot be avoided\b",
    r"\byou must never\b",
    r"\b(?:no possibility of|off the cards for|barred from|prohibited from|forbidden from|forbids you from)\b.{0,25}\b(?:marriage|marrying|matrimony|wed(?:ding)?)\b",
    r"\b(?:marriage|wedding) is (?:off the cards|prohibited)\b",
    r"\bdivorce is (?:the )?inevitable\b",
    r"\bdictates you should not wed\b",
    r"\b(?:destined for separation|doomed to (?:collapse|fail)|headed for (?:failure|breakup)|leads to breakup)\b.{0,25}\b(?:marriage|marital|union|partnership|relationship|married life|wedding)\b",
    r"\b(?:marriage|marital|union|partnership|relationship|married life|wedding)\b.{0,25}\b(?:destined for separation|doomed to (?:collapse|fail)|headed for (?:failure|breakup)|leads to breakup)\b",
    r"\bwill wreck your married life\b", r"\bwedding prospects are ruined\b",
    r"\bspells disaster for your\b.{0,15}\b(?:union|marriage|relationship)\b",
    r"\bguarantees marriage problems\b", r"\byour relationship will crumble\b",
    r"\b(?:will not|never) ever encounter a\b.{0,15}\b(?:spouse|partner|husband|wife)\b",
    r"\bno (?:husband|wife|spouse|partner|life partner)\b.{0,20}\bwill (?:ever )?come into your life\b",
    # Anchored to the marriage/spouse noun as subject — found by review not
    # to be, and a bare "X is something you will never have" also matches
    # ordinary hedges ("certainty is something you will never have from a
    # chart alone"), which is caution language, not marriage fatalism.
    r"\b(?:spouse|partner|husband|wife|life partner|marriage)\b.{0,20}\bis something you will never have\b",
    r"\bno escaping this fate\b",
    # Negative lookahead excludes a trailing conditional ("...unavoidable
    # only if you ignore practical choices") — found by review to also
    # match that qualified, non-fatalistic phrasing, which reads as advice
    # to act, not a fixed outcome.
    r"\bthis (?:outcome|fate) is unavoidable\b(?!\s*,?\s*(?:only\s+)?if\b|\s*unless\b)",
    r"\bcannot dodge what is written\b",
    # 2026-08-09 (Qwen's audit): domain-agnostic poetic-fatalism phrasing,
    # same category as "no escaping this fate" above — not caught by the
    # windowed verb+subject check below because these use vocabulary
    # ("fated", "sentenced", "barren", "blocked by...alignment") that check
    # doesn't cover, and is specific/rare enough not to need generalizing
    # into that machinery.
    # Excludes bare "end" — a dasha/transit period legitimately "ends" all
    # the time ("this dasha is fated to end in March" would be ordinary
    # period language, not fatalism), found by review.
    r"\bfated to (?:dissolve|fail|collapse)\b",
    r"\bsentenced (?:you|your \w+) to (?:struggle|hardship|poverty|childlessness|failure)\b",
    r"\b(?:womb|fertility) is (?:cosmically |permanently )?barren\b",
    r"\bbirth is blocked by\b",
    r"\bis your inescapable destiny\b",
)

# 2026-08-09 (Qwen's wealth/children audit). History worth reading before
# touching this block — it's had five independent review rounds, four of
# which found real bugs:
#
# Rounds 1-2: a *generic* mechanism (any of a dozen "fatalism verbs" matched
# against any of a handful of "domain subject" words, via a character
# window or clause-splitting) had no negation handling, then a negation fix
# that still missed forms, mishandled punctuation, made one verb pattern
# permanently self-disqualifying, and shipped a regex missing a `\b` that
# matched "certain" *inside* "uncertain" — flagging a hedge as its opposite.
# Round 3 abandoned that mechanism for explicit phrase matching (this
# tuple), the same style already proven clean on the marriage patterns
# above — plus one shared negation check, `_negation_precedes()`, applied
# at the time to *all* of `_DOSHA_OVERCLAIM_OUTPUT` including marriage.
# Rounds 4-5 found that sharing was itself the bug: each attempt to widen
# `_negation_precedes()`'s scope (sentence-wide, then clause-wide with a
# conjunction rule) fixed some false negatives while reopening others, and
# because it ran over the *whole* list, every miss reached the marriage
# patterns too — a net regression against `main`, which had been correct
# there for three rounds straight *without* any negation check at all.
#
# The fix, finally: stop trying to make one negation heuristic correct for
# all of English grammar, and stop running it over patterns that never
# needed it. `_negation_precedes()` (below) is now called only for this
# tuple, not the marriage/poetic one above — marriage goes back to the
# exact bare `re.search()` it had for three clean rounds. This tuple's
# patterns are still explicit phrases, matched with the negation check,
# because "does not mean you will never have children" contains the bad
# phrase as a literal substring by construction (that's how a reassurance
# sentence is built), so *some* negation awareness is unavoidable here in
# a way it never was for marriage's patterns. What's true and stays true:
# a lexical negation heuristic cannot resolve every English construction
# (a non-restrictive relative clause — "this dosha, which is not minor,
# guarantees poverty" — is genuinely ambiguous to a comma/conjunction rule).
# That's an accepted, documented limitation, not a bug to keep chasing.
_WEALTH_CHILDREN_OVERCLAIM_OUTPUT = (
    r"\byou will always struggle financially\b",
    r"\bguarantees? you will never accumulate wealth\b",
    r"\bdictates? permanent poverty\b",
    r"\bcursed by this (?:dosha|yoga|placement) and will never improve\b",
    r"\bcondemns? you to lifelong financial hardship\b",
    r"\bdoomed to remain poor\b",
    r"\bseals? your fate\b",
    r"\b(?:wealth prospects|financial (?:future|prospects))\b.{0,15}\bpermanently blocked\b",
    r"\bfinancial ruin is guaranteed\b",
    r"\bforbids? you from ever becoming wealthy\b",
    r"\bdestined for poverty\b",
    r"\bmakes? poverty certain\b",
    r"\bguarantees? poverty\b", r"\bpoverty is guaranteed\b",
    r"\bcannot be undone\b.{0,30}\b(?:poverty|struggl\w+ financially)\b",
    r"\byou will never have children\b",
    r"\bguarantees? you will remain childless\b",
    r"\bcondemns? you to a childless life\b",
    r"\bdoomed to never bear children\b",
    r"\bforbids? you from ever having (?:a child|children)\b",
    r"\byou will never conceive\b",
    r"\bdictates? (?:that )?you will remain without offspring\b",
    r"\bchances? of having children are permanently blocked\b",
    r"\bchildlessness is guaranteed\b",
    r"\bdestined to remain childless\b",
    r"\bensures? you will remain childless\b",
    r"\bguarantees? childlessness\b",
    r"\bcannot be undone\b.{0,30}\b(?:will never have children|will never conceive|remain childless)\b",
)

# Shared by every pattern above (not per-pattern lookbehinds — those don't
# scale and were the direct cause of round 2's bugs): a match is ignored if
# a negation cue appears earlier in the *same clause* — not the same
# sentence, and this distinction is itself the fix for a bug a fourth
# independent review found: scoping to the whole sentence let an unrelated
# negation anywhere in it (across a comma, a dash, a "but") suppress a real,
# semantically unrelated violation later in that sentence, and because this
# check runs over the *entire* `_DOSHA_OVERCLAIM_OUTPUT` list, that widened
# hole reached the marriage patterns too — a net regression against `main`,
# not just a wealth/children issue. `_CLAUSE_BOUNDARY` below is deliberately
# not a bare comma, though: "It does not, in any reading, guarantee
# poverty." needs the negation to reach across two commas to the verb it
# genuinely negates. The distinction that matters is whether a comma/dash
# is followed by a coordinating conjunction (and/but/so/...) — that pattern
# reliably means "new clause", where a bare comma inside a parenthetical
# aside does not.
#
# Backward-only because negation in English overwhelmingly precedes what it
# negates ("does not guarantee X", "is never guaranteed", "no chart
# guarantees X"). The forward-only lookahead this review round's PR had for
# "guarantees nothing" was removed entirely — the fourth review proved it
# both unnecessary (no test needs it; the explicit patterns don't produce
# that shape) and actively harmful (it doesn't respect sentence/clause
# boundaries at all, so "This dosha guarantees poverty — nothing can change
# it." was incorrectly cleared by an intensifier, not a negation, sitting
# right after the real violation).
_NEGATION_CUES = re.compile(
    r"\b(?:does not|do not|did not|will not|cannot|is not|are not|was not|"
    r"were not|is never|never guarantees?|never means?|"
    # No trailing "guarantees?" on "chart/placement/dosha/yoga" deliberately
    # — the backward search stops right before the overclaim match itself,
    # so "guarantees" (the word several overclaim patterns start with) is
    # never part of the text available to search; requiring it here would
    # mean the cue could never match "no chart guarantees poverty" at all.
    # A version of this file briefly required "guarantees?" uniformly,
    # worried that a bare "no dosha" would collide with fatalistic phrasing
    # like "there is no dosha stronger than this one, your marriage will
    # fail" — but that collision is now moot for two independent reasons:
    # marriage doesn't run this negation check at all (see the docstring on
    # `dosha_overclaim_kind` below), and for wealth/children, the comma in
    # that exact shape is now itself an unconditional clause boundary
    # (`_CLAUSE_BOUNDARY`), so "no dosha" in the clause before a comma can
    # never reach a match in the clause after it regardless of this list.
    # "remedy" is kept requiring "guarantees?" though — "no remedy can
    # undo/fix this" is itself fatalistic phrasing (used by the explicit
    # patterns above, same clause, no comma involved), the opposite of a
    # hedge; only "no remedy guarantees X" is the reassuring form.
    r"no (?:chart|placement|dosha|yoga)\b|no remedy guarantees?|"
    r"not mean|is a myth|myth that|misconception|untrue|"
    r"wrongly claim|falsely claim|is false that|not true that|not forbid|"
    # "can" was briefly excluded here too, worried "no one can undo this
    # dosha" reads as fatalistic emphasis rather than a hedge — same
    # reasoning, same fix: the comma boundary already separates that
    # emphasis from an unrelated claim after it, so "can" doesn't need to
    # be excluded to prevent the collision.
    r"should (?:never|not) (?:ever )?(?:tell you|say|claim)|"
    r"no (?:astrologer|one|reading|chart) (?:should|can)|"
    r"ignore any reading that claims|reading that claims|"
    r"nothing (?:in|about)|nobody|"
    r"by no means)\b"
)
# Every comma, dash (em or en), colon, and sentence-ending mark is a hard
# clause boundary — deliberately unconditional, not conjunction-aware. An
# earlier version tried to tell "comma starts a new independent clause"
# ("remedies cannot help, and this dosha guarantees poverty") apart from
# "comma introduces a parenthetical aside around the same verb" ("it does
# not, however, guarantee poverty") by checking for a following
# conjunction. A fifth independent review proved that distinction isn't
# resolvable lexically in either direction — both shapes use the exact same
# comma-plus-word pattern, and no fixed word list can tell them apart
# without actually parsing the sentence.
#
# Given that, and given CLAUDE.md's explicit "never suppress" framing for
# dosha fatalism, this deliberately biases toward the safer failure mode: a
# comma-joined parenthetical aside around a real hedge occasionally gets
# flagged (costing one repair-cycle regeneration — orchestrator.py's single
# retry — not a shipped violation), rather than a comma-joined independent
# clause silently letting a real fatalistic verdict through uncaught.
# Constructions like "it does not, in any reading, guarantee poverty" or a
# non-restrictive relative clause ("this dosha, which is not minor,
# guarantees poverty") are a known, accepted limitation of a lexical
# approach — not a bug to keep chasing back and forth across review rounds.
_CLAUSE_BOUNDARY = re.compile(r"[.;:!?,]|—|–|--")


def _negation_precedes(normalized: str, start: int) -> bool:
    clause_start = 0
    for boundary in _CLAUSE_BOUNDARY.finditer(normalized, 0, start):
        clause_start = boundary.end()
    return bool(_NEGATION_CUES.search(normalized[clause_start:start]))


def dosha_overclaim_kind(answer: str) -> str | None:
    """Non-null when an answer states a dosha/yoga as a fixed, absolute
    outcome instead of the classical flag-with-context it always is.

    Marriage/poetic patterns (`_DOSHA_OVERCLAIM_OUTPUT`) are checked with a
    bare `re.search` — no negation awareness — because that's exactly what
    was proven correct across three independent review rounds; adding a
    shared negation check to them in rounds 3-4 introduced regressions that
    weren't there before. Wealth/children patterns need the negation check
    (`_negation_precedes`) because their phrasing gets wrapped in "does not
    mean X" reassurances that contain the bad phrase as a literal
    substring — a problem marriage's patterns don't have."""
    normalized = _normalize(answer)
    for pattern in _DOSHA_OVERCLAIM_OUTPUT:
        if re.search(pattern, normalized):
            return "dosha_overclaim"
    for pattern in _WEALTH_CHILDREN_OVERCLAIM_OUTPUT:
        for match in re.finditer(pattern, normalized):
            if not _negation_precedes(normalized, match.start()):
                return "dosha_overclaim"
    return None
