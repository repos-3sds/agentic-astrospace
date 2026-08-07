"""Refer-out safety gate — shared by every agent surface (Ask, domain
agents, and any future one).

Deliberately not agent-owned: distributing this into each domain agent's
own prompt/logic is how the boundary drifts out of sync between them. It
wraps the orchestrator once, before any model call, and again on the way
out.
"""
import re

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
    normalized = " ".join(question.casefold().split())
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
_PROHIBITED_OUTPUT = (
    (r"\byou (?:will|are going to) die\b", "death"),
    (r"\byour (?:death|lifespan|life expectancy)\b", "death"),
    (r"\byou (?:will|are likely to) live (?:until|to|for)\b", "death"),
    (r"\byou have\b.{0,24}\b(?:years|months) (?:left|to live)\b", "death"),
    (r"\byou (?:have|are suffering from)\b.{0,24}\b(?:cancer|disease|tumou?r)\b", "health"),
    (r"\b(?:stop|start|change) (?:taking )?your (?:medication|medicine|insulin)\b", "health"),
    (r"\byou will (?:win|lose) (?:the|your) (?:case|lawsuit|appeal)\b", "legal"),
    (r"\byou (?:will|should) (?:buy|sell|invest in)\b.{0,24}\b(?:stock|share|crypto)\b", "money"),
)


def prohibited_verdict(answer: str) -> str | None:
    """Which boundary an answer crosses, if any. None means it is clean."""
    normalized = " ".join(answer.casefold().split())
    for pattern, kind in _PROHIBITED_OUTPUT:
        if re.search(pattern, normalized):
            return kind
    return None


# "A dosha is a flag, not a verdict" (CLAUDE.md, non-negotiable) had only a
# prompt instruction, no net — unlike refer-out's input+output pair. Written
# marriage-first: manglik/gandanta/grahan dosha is exactly where this fails
# if it's weak, and marriage is the first sensitive domain shipping with it.
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
)


def dosha_overclaim_kind(answer: str) -> str | None:
    """Non-null when an answer states a dosha/yoga as a fixed, absolute
    outcome instead of the classical flag-with-context it always is."""
    normalized = " ".join(answer.casefold().split())
    for pattern in _DOSHA_OVERCLAIM_OUTPUT:
        if re.search(pattern, normalized):
            return "dosha_overclaim"
    return None
