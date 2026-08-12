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
    # Found missing by a fourth review of the foreign-domain immigration
    # patterns: "how likely"/"odds of" are verdict-seeking frames just as
    # much as the "chances? of"/"likelihood" already here, and their
    # absence meant a subject match (e.g. "how likely is my visa
    # approval") never reached `seeks_verdict` at all. Not immigration-
    # specific — this closes the same phrasing family across every
    # domain the subject list already covers (legal/health/money too).
    r"\bhow likely\b", r"\bodds of\b",
    # Found by a fifth review: "probability" is a verdict-seeking frame
    # exactly like "chances? of"/"likelihood" already here — "what's the
    # probability my visa gets approved" never reached `seeks_verdict`.
    r"\bprobability\b",
    # 2026-08-12 (Codex, reviewing PR #45): "I have been feeling sick
    # lately, any advice?" named the health subject but sought no frame
    # already listed here — "any advice" is a request for medical guidance
    # exactly as directly as "what should i do", which already worked only
    # because it happens to contain "should i" as a substring. Not a health-
    # specific gap: an advice-seeking frame paired with any prohibited
    # subject (a legal or financial "any advice?" equally) was passing the
    # gate on phrasing alone, same class of miss as the immigration/
    # probability additions above.
    r"\bany advice\b", r"\bwhat advice\b", r"\badvice (?:on|for|about)\b",
    r"\bany (?:tips|suggestions|recommendations)\b", r"\bwhat should\b",
)

# Shared immigration-process vocabulary — one constant, not duplicated
# per pattern. A second independent review of the first version (which
# *did* duplicate it, once per direction) found real drift between the
# copies: `approved?` etc. only makes the trailing letter optional, not
# the whole "-ed" suffix, so "denied"/"rejected"/"granted"/"accepted"
# silently had no bare-verb form at all despite reading as if they did —
# and the reverse-order copy had quietly dropped several outcome words
# the forward copy had. Concatenation (not an f-string) deliberately,
# so the regex's own `{0,24}` quantifier braces never collide with
# Python's f-string brace syntax — the exact kind of subtle bug this
# constant exists to stop happening again.
# "residency" deliberately narrowed to the immigration sense — a third
# review found the bare word collides with a doctor's medical residency
# ("will I get selected for my medical residency match"), and combined
# with the get/select outcome verbs below, over-fired on ordinary
# career-timing questions the product exists to answer.
#
# A fifth review found the round-4 narrowing ("permanent residency"/"us
# residency"/"residency petition|visa") was US-only, but this domain is
# "Foreign Travel & Settlement" — not "US Immigration" — and covers
# settling in any country by construction. "will I get UK residency",
# "canada residency", "dubai residency" all went uncaught. Rather than
# re-widen the bare word (which reopens the medical/academic/tax
# collision round 3-4 closed), added an explicit country/region list —
# closes the demonstrated gap without touching the collision-prone bare
# form; a country not in this list is an accepted, documented residual
# limitation of a lexical approach, not a bug to keep chasing.
_RESIDENCY_COUNTRIES = (
    r"uk|united kingdom|canada|canadian|australia|australian|uae|dubai|"
    r"eu|european union|schengen|germany|german|new zealand|singapore|"
    r"ireland|irish"
)
_IMMIGRATION_SUBJECTS = (
    r"visa|green ?card|immigration|citizenship|work permit|h-?1-?b|"
    # Both a prefix ("permanent"/"us") and a suffix (application/status/...)
    # were optional here in an earlier version, which meant neither was
    # actually required — bare "residency" still matched, undoing the
    # narrowing entirely. A fourth review found the FIX for that also had
    # a version of the same bug one level down: "residency application" is
    # the standard phrase for a medical/academic residency application,
    # and "residency status" is the standard phrase for *tax* residency —
    # so those two suffixes reintroduced exactly the collision they were
    # meant to close. Dropped both; "petition"/"visa" aren't used outside
    # the immigration sense and lose nothing demonstrated.
    r"(?:permanent residency|us residency|residency (?:petition|visa)|"
    r"(?:" + _RESIDENCY_COUNTRIES + r") residency|"
    r"residency (?:in|for) (?:the )?(?:" + _RESIDENCY_COUNTRIES + r"))|"
    r"asylum|naturalization|"
    # A fifth review found several immigration-specific nouns entirely
    # missing: bare "petition" ("will my petition be denied"), "USCIS" as
    # the deciding agent ("will USCIS approve my application"), and a
    # handful of status categories that are exactly this domain's subject
    # matter, not edge cases.
    r"petition|parole|refugee status|daca|tps|adjustment of status|"
    r"extension of stay|uscis|"
    # Form numbers (I-485, N-400, ...) — narrow, unambiguous pattern, low
    # collision risk since the "letter-dash-3 digits" shape is specific to
    # USCIS forms.
    r"[in]-\d{3}"
)
# Verb AND noun forms — a third review found only verbs were covered, so
# "what are my chances of a green card approval" (no verb at all) slipped
# through one word away from a phrase already pinned as caught. A fourth
# review found that noun-form fix had itself only been applied to half of
# this constant's own verb families ("approve"/"reject"/"deny"/"refuse"/
# "accept"/"issue" got nouns; "succeed"/"fail"/"select"/"clear" didn't) —
# the drift moved from between copies of this constant to within it.
# "will my visa application be successful" is arguably the single most
# common phrasing of this whole question and had no coverage at all.
_IMMIGRATION_OUTCOME_VERBS = (
    r"approve[ds]?|approving|approvals?|reject(?:ed|s|ing)?|rejections?|"
    r"den(?:y|ies|ied|ying)|denials?|refuse[ds]?|refusing|refusals?|"
    r"grant(?:ed|s|ing)?|accept(?:ed|s|ing)?|acceptances?|"
    r"succeed(?:ed|s|ing)?|success(?:es|ful|fully)?|"
    r"fail(?:ed|s|ing)?|failures?|go(?:es|ing)? through|"
    r"went through|comes? through|coming through|came through|"
    r"get(?:s|ting)?|got|receive[ds]?|receiving|obtain(?:ed|s|ing)?|"
    r"issue[ds]?|issuing|issuance|clear(?:ed|s|ing)?|clearances?|"
    r"select(?:ed|s|ing)?|selections?|revoke[ds]?|revoking|revocations?|"
    r"cancel(?:led|ed|s|ling|ing)?|cancellations?|turn(?:ed|s|ing)? down|"
    r"wins?|won|lose[s]?|lost|"
    # A fifth review found "pass" ("will I pass my citizenship interview")
    # and "go well" ("will my visa interview go well") — both common,
    # natural phrasings — entirely uncovered. "renew" is the standard verb
    # for the status categories (DACA, TPS) added alongside it and was
    # missing for the identical reason (found during this round's own
    # verification probe, not the review itself — DACA/TPS are commonly
    # asked about as renewals, not one-time approvals).
    r"pass(?:ed|es|ing)?|go(?:es|ing)? well|renew(?:ed|s|ing|als?)?"
)
# Future-framing words, shared the same way — a third review found this
# scaffolding was still copy-pasted per pattern (once per output-net arm)
# even after the vocabulary itself was de-duplicated, and had drifted the
# identical way: "are going to" (the plural of an already-listed phrase)
# and an adverb gap were present in one copy and missing from another.
_FUTURE_FRAMING = (
    r"will|shall|is going to|are going to|is certain to|are certain to|"
    r"is guaranteed to|are guaranteed to|is bound to|are bound to|"
    # A fifth review found the output net required an explicit
    # will/shall/certain-to framing word, but a model doesn't have to
    # phrase a prediction that way — hedged/probabilistic certainty
    # language ("has a high chance of approval", "is highly likely to be
    # approved") is exactly how an LLM plausibly phrases the same verdict,
    # and this is the *last* layer; nothing catches it after. Shared here
    # (not duplicated per output arm) for the same reason every other
    # scaffolding constant in this file is shared.
    r"has a high chance of|has a good chance of|has an excellent chance of|"
    r"is highly likely to be|is very likely to be|is likely to be"
)
_ADVERB_GAP = r".{0,16}"

# 2026-08-10 (validation-loop handoff §3, verified before fixing): the death
# cluster in `_PROHIBITED_OUTPUT` below was anchored entirely to "you", so a
# longevity verdict about anyone else passed straight through. Measured on the
# shipped code, 10 of 12 probes were missed — "your spouse will die young",
# "your child will not survive", "your father will die in 2029", "he will die
# soon" — against 'you will die young' and 'your lifespan is short' being
# caught. Same category of gap as the contraction one at the top of this file:
# the rule was right and its subject list was one case wide.
#
# This matters specifically now. Once the validation loop stores reader-
# reported life events, bundles start carrying third-party context ("reader
# reported a family bereavement in 2019") and the model has a reason to write
# about a family member's lifespan that it never had before. Closing it after
# that data exists would be closing it late.
#
# People only, deliberately: "marriage"/"partnership"/"business" are NOT here
# because the noun cluster below (lifespan/life expectancy/longevity) has an
# ordinary non-death use with abstract subjects — "the longevity of your
# marriage" is a legitimate sentence this app might well write, and adding
# abstract nouns would flag it. Third-party pronouns are covered separately,
# with explicit death VERBS only, for the same reason.
_THIRD_PARTY_SUBJECTS = (
    r"spouse|husband|wife|partner|fianc(?:e|é|ee|ée)|"
    r"child|children|kid|son|daughter|baby|"
    r"father|mother|dad|mom|mum|parent|parents|"
    r"brother|sister|sibling|"
    r"grandfather|grandmother|grandparents?|grandpa|grandma|"
    r"father-in-law|mother-in-law|in-law|"
    r"family member|relative|friend"
)
# "your father", "your father's", "your fathers'" — plus the bare pronouns,
# which take no "your". Written once and shared by every death pattern below,
# following this file's own hard-learned rule that a vocabulary list copied
# per-pattern drifts between the copies.
_THIRD_PARTY_REF = (
    r"(?:your (?:" + _THIRD_PARTY_SUBJECTS + r")(?:'s|s')?|he|she|they)"
)
# First and third person in one subject, so the lifespan patterns below cannot
# drift apart between the two the way the immigration vocabulary once drifted
# between its copies. The 2026-08-11 review found exactly that drift already
# starting: "your husband will live past 60" was caught while "you will live
# past 90" was not, because the first-person arm was a separate, older, shorter
# pattern. One subject, one set of arms.
_LIFE_SUBJECT = r"\b(?:you|" + _THIRD_PARTY_REF + r")\b"
_HAS_SUBJECT = (
    r"\b(?:you have|your (?:" + _THIRD_PARTY_SUBJECTS + r")(?:'s|s')? has|"
    r"he has|she has|they have)\b"
)
_MODAL = r"\b(?:will|shall|is going to|are going to|is likely to|are likely to)\b"

# What makes "live" a lifespan claim is the OBJECT, not the verb — this is the
# whole fix for the 2026-08-11 review's B3. The previous patterns matched
# `live (?:until|to|for|past|beyond)` and stopped there, which swallows the
# enormously common "live to <verb>" construction and the "live beyond one's
# means" idiom:
#
#   flagged | He will not live beyond his means during this dasha.
#   flagged | Your father will live to enjoy his retirement.
#   flagged | He will live to see the business succeed.
#
# That is not cosmetic. A match here REPLACES the entire answer with the
# longevity refer-out, so a false positive costs a reader their reading and
# tells them the app will not discuss their lifespan — about a question they
# never asked.
#
# So the object has to be something only a lifespan claim puts there: an age or
# year, or the "old age" idiom. "for" is dropped from the preposition list
# entirely — "live for three years in Dubai" is a foreign-residence sentence,
# and the genuine longevity form of it ("live for another 40 years") is its own
# pattern with `another` required.
#
# Spelled-out numbers are covered as well as digits. A model writes "about
# three years left" at least as readily as "3", and the pattern this replaces
# happened to catch that only because it required no number at all — which was
# the same looseness that made it fire on ordinary dasha language.
_DURATION_COUNT = (
    r"\d+|a few|several|a couple of|one|two|three|four|five|six|seven|eight|"
    r"nine|ten|eleven|twelve|eighteen|twenty|thirty|forty|fifty"
)
_LIFESPAN_OBJECT = (
    r"(?:the age of |age )?\d{1,4}\b"
    r"|(?:the age of |age )?(?:sixty|seventy|eighty|ninety|a hundred)(?:[- ]\w+)?\b"
    r"|(?:a )?(?:ripe )?old age"
    r"|(?:his|her|their|your) (?:sixties|seventies|eighties|nineties)"
)

# Either party. Used by the death-as-a-NOUN rows, which apply identically to
# the reader and to anyone they asked about — the gap those rows close was
# present for both, precisely because first- and third-party patterns were
# maintained as two separate lists and drifted. One reference group means a
# relation added here is covered on both sides at once, rather than being
# remembered in one list and forgotten in the other.
_PERSON_REF_BODY = r"you|your (?:" + _THIRD_PARTY_SUBJECTS + r")(?:'s|s')?|he|she|they"

# A PERSON, never a bare possessive. The first version of this constant
# included a bare "your", which made it a possessive anchor: every "your
# <anything>" satisfied it, so "your business will come to an untimely end"
# read as a death verdict. The name said person; the pattern said possessive.
_DEATH_NOUN_REF = r"(?:" + _PERSON_REF_BODY + r")"

# Same, plus possessive pronouns. Used only where the predicate itself is
# unambiguous ("short-lived", "life … cut short"), so the anchor carries less
# weight than it does on rows like "end" where the noun has ordinary uses.
_DEATH_NOUN_REF_POSS = r"(?:his|her|their|" + _PERSON_REF_BODY + r")"

# Gap between a person reference and the death noun. Sentence-bounded rather
# than `.{0,N}` because `_normalize()` collapses a whole multi-paragraph answer
# onto one line: an unbounded gap let "…affects your career. An untimely end to
# this job phase…" match across the full stop, so the true false-positive rate
# on real answers was far higher than single-sentence testing suggested.
_SAME_SENTENCE = r"[^.!?;]{0,40}?"

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
        # 2026-08-10 (personality domain, independent-review round 1): mood/
        # affect vocabulary was entirely missing from this subject list —
        # only the clinical stems (depress/suicid/mental health) were
        # covered, so a verdict-seeking question naming ordinary anxiety/
        # panic language ("will my anxiety ever go away") reached no gate
        # at all. Added here (not as a subject-alone category like death)
        # to keep the existing two-part subject+seeks_verdict design: this
        # only fires when the question also asks for a verdict, the same as
        # every other health subject above. Two reviewers independently
        # found that a *fully* open self-reflective phrasing ("is this
        # just my temperament?", "does my chart's character explain this?")
        # still won't be caught even with this addition, because it names
        # no _VERDICT_FRAMES word at all — widening that shared, cross-
        # domain frame list to catch open reflection questions would raise
        # false-positive risk for every domain, not just this one, so it's
        # accepted as a residual limitation here; the personality addendum
        # is the second line of defense for that shape of question, not
        # this gate.
        r"\banxi(?:ety|ous)\b", r"\bpanic attacks?\b", r"\bpanick(?:y|ing)\b",
        r"\bfeel(?:ing)? (?:hopeless|worthless|numb)\b", r"\bmood swings?\b",
        r"बीमारी", r"అనారోగ్య", r"వ్యాధి",
    )),
    ("legal", (
        r"\blegal advice\b", r"\bsue\b", r"\blawsuit\b", r"\bcourt\b",
        r"\bjudge\b", r"\bjury\b", r"\bverdict\b", r"\bprison\b",
        r"\bjail\b", r"\bconvict", r"\bacquit", r"\bguilty\b",
        r"\bcase\b.{0,20}\b(?:win|lose|outcome)\b", r"\bbail\b",
        r"\bcustody\b", r"\bdivorce settlement\b",
        # 2026-08-09 (foreign domain review, two rounds): the original
        # "visa...approved/rejected" entry only covered one exact phrasing.
        # This PR is what turns that gap from a safe domain_not_ready
        # refusal into a live agent answer, since the foreign domain
        # routes exactly this vocabulary. Both directions, using the
        # shared vocabulary above so the two arms can't drift again.
        r"\b(?:" + _IMMIGRATION_SUBJECTS + r")s?\b.{0,24}\b(?:" + _IMMIGRATION_OUTCOME_VERBS + r")\b",
        # Negative lookahead excludes "get my visa photos taken"/"get my
        # green card application started" — "get" immediately followed by
        # the subject reads as receiving it as a final outcome ("will I
        # get my green card") in general, but not when the subject is
        # itself modifying a process/document noun that follows it. A
        # third review found this the one case narrowing to a tight gap
        # or an exclusion list can't fully solve (English is genuinely
        # ambiguous here even for a human reader without more context) —
        # this closes the two demonstrated instances; broader "get + visa
        # + [process noun]" phrasing beyond these is an accepted,
        # documented residual limitation of a lexical approach, not a bug
        # to keep chasing.
        r"\b(?:" + _IMMIGRATION_OUTCOME_VERBS + r")\b.{0,24}\b(?:" + _IMMIGRATION_SUBJECTS + r")s?\b"
        r"(?!\s+(?:photos?|pictures?|application (?:started|going|in progress)|paperwork|documents?))",
        # Deportation is asked about the outcome by construction ("will I
        # get deported"), so it's a bare subject like the others here,
        # still gated by the shared seeks_verdict frame check below.
        r"\bdeport(?:ed|ations?)?\b",
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
    # The subject slot is optional, so this one pattern covers both "your
    # death"/"your lifespan" (what it always caught) and "your father's
    # death"/"your spouse's lifespan" (what it did not).
    (r"\byour (?:(?:" + _THIRD_PARTY_SUBJECTS + r")(?:'s|s')? )?"
     r"(?:time of )?(?:death|dying|lifespan|life expectancy|longevity)\b", "death"),
    # Death verbs, first and third person through one shared subject. Adverb-gap
    # tolerant ("your spouse will soon die") and negation-tolerant, because a
    # survival verdict is a death verdict with the polarity flipped — "your
    # child will not survive" is not a hedge, it is the prohibited sentence.
    (_LIFE_SUBJECT + _ADVERB_GAP + _MODAL + r"\s*(?:not\s+)?" + _ADVERB_GAP +
     r"\b(?:die|dying|pass away|passing away)\b", "death"),
    # Survival verbs, negated. `live` is deliberately NOT in this arm — see
    # `_LIFESPAN_OBJECT`; "your daughter will not live at home much longer" is
    # an ordinary sentence about moving out, and it matched here until the
    # lifespan arms below took the verb over.
    # "make it" carries `(?!\s+to\b)` because bare "make it" is only mortal
    # when nothing follows it: "will not make it", "will not make it through
    # the winter". "will not make it TO <something>" is ordinary English about
    # missing an event — "your son will not make it to your birthday dinner"
    # was being read as a death verdict. The genuinely mortal "make it to" is
    # "make it to 50" / "to old age", and that is already covered by the
    # age-object row further down, which requires the age.
    (_LIFE_SUBJECT + _ADVERB_GAP +
     r"\b(?:will|shall|is going to|are going to|can|is able to|are able to)\b\s*not\b" +
     _ADVERB_GAP + r"\b(?:surviv|pull through|make it\b(?!\s+to\b))", "death"),
    # Negated "live long" — the one lifespan claim that fits NEITHER arm, and
    # so was missed for BOTH parties: "you will not live long" and "your mother
    # will not live long" both passed straight through. The verb arm above
    # deliberately excludes `live`, and the object arm below keys on an age
    # ("live to 80"), which "long" is not. That leaves the single most direct
    # phrasing of the verdict uncovered.
    #
    # `live` must be IMMEDIATELY followed by the duration word. That is what
    # keeps out the sentence this file already calls out as ordinary — "your
    # daughter will not live at home much longer" — where "at home" intervenes.
    # It also leaves "he will not live beyond his means" alone, since "beyond"
    # is not in this list.
    (_LIFE_SUBJECT + _ADVERB_GAP +
     r"\b(?:will|shall|is going to|are going to|may|might)\b\s*not\b" + _ADVERB_GAP +
     r"\blive (?:long|much longer|very long|for long)\b", "death"),
    # ── "live", which is where this gets delicate ────────────────────────────
    # A lifespan claim is identified by its OBJECT, never by the verb: "will
    # live to 80" is a verdict, "will live to see the business succeed" is not.
    (_LIFE_SUBJECT + _ADVERB_GAP + _MODAL + r"\s*(?:not\s+)?" + _ADVERB_GAP +
     r"\blive (?:until|to|past|beyond)\s+(?:" + _LIFESPAN_OBJECT + r")", "death"),
    (_LIFE_SUBJECT + _ADVERB_GAP + _MODAL + _ADVERB_GAP +
     r"\blive (?:for )?another (?:" + _DURATION_COUNT + r")\s*(?:years?|decades?|months?)\b", "death"),
    (_LIFE_SUBJECT + _ADVERB_GAP + _MODAL + _ADVERB_GAP +
     r"\blive a (?:long|short|brief) life\b", "death"),
    # The one place polarity alone decides it. "He will live to see the
    # business succeed" is ordinary; "your father will not live to see the
    # wedding" is a death verdict about the same event, and the only thing
    # separating them is the "not". Excludes "live up to", which is a different
    # verb phrase entirely ("will not live up to expectations").
    #
    # "regret" is excluded for the same reason, found while unblocking this
    # guard: "you will not live to regret this decision" is an idiom of
    # REASSURANCE and was reading as a death verdict. Pre-existing, not
    # introduced by the third-party work. "live to tell the tale" stays caught
    # — negated, that one really is about not surviving.
    (_LIFE_SUBJECT + _ADVERB_GAP +
     r"\b(?:will|shall|is going to|are going to)\b\s*not\b" + _ADVERB_GAP +
     r"\blive to (?!regret\b)\w+", "death"),
    # Subject-free on purpose: "has a short lifespan" carries the whole
    # verdict whoever it is about, and the noun forms here have no ordinary
    # non-death use the way the abstract-subject case discussed above does.
    (r"\b(?:short|limited|brief|reduced|curtailed) (?:lifespan|life span|life expectancy)\b", "death"),
    # 2026-08-11, independent verification of the third-party pass above:
    # tested against a phrase set written separately from that pass's own
    # tests, which exposed that every death pattern here — first- AND
    # third-party — matched death as a VERB ("die", "not survive", "not
    # live long") and nothing matched it as a NOUN. So "your son will have
    # a short life", "your partner will meet an early death" and "your
    # spouse will suffer a fatal accident" all passed the net while their
    # verb equivalents were caught. Confirmed pre-existing and symmetric:
    # "you will have a short life" missed identically, so this is inherited
    # from the original table rather than introduced by the third-party
    # work, and it is closed for both parties here in one place.
    #
    # ── What the first attempt got wrong, since the corrections below only
    # make sense against it. Independent review broke it in both directions:
    #
    #  1. `_DEATH_NOUN_REF` contained a bare "your", so it anchored on a
    #     POSSESSIVE rather than a PERSON, and every "your <anything>"
    #     satisfied it: "your business will come to an untimely end" and
    #     "your Mercury antardasha comes to a sudden end" both read as death
    #     verdicts. The comment claimed it was a person anchor; the code was
    #     not. That also silently reintroduced what an earlier review round
    #     had removed further down this file, where bare "end" was excluded
    #     precisely because dashas and transits legitimately end all the time.
    #  2. "passing" was treated as subject-free, colliding with this app's own
    #     vocabulary for a transit — "the sudden passing of Mars over your
    #     ascendant". Same class of error as "life", one row apart.
    #  3. "(?:\w+ )?(?:birthday|years)" swallowed "teenage years",
    #     "retirement years", "golden years".
    #  4. The gaps used `.{0,32}` while `_normalize()` flattens a whole
    #     multi-paragraph answer to one line, so a match could span a full
    #     stop.
    #
    # The root cause of all four was the same, and it is worth naming because
    # it is the identical failure this block was written to fix: the negative
    # tests avoided the word "your", which is the word these patterns key on,
    # so "no false positives" was measuring nothing. Negatives now carry
    # "your" against every person-anchored row.
    #
    # Two anchoring rules, applied consistently:
    #  - Subject-free ONLY where the noun cannot describe anything but a
    #    person's death: "death" and "demise". "passing" and "end" fail that
    #    test in this domain and are person-anchored instead.
    #  - Person anchors are `you` or `your <relation>` (pronouns included via
    #    _THIRD_PARTY_REF) — never a bare possessive.
    (r"\b(?:early|untimely|premature|sudden|violent) (?:death|demise)\b", "death"),
    # "fatal" restricted to bodily nouns: bare "fatal" eats "a fatal flaw in
    # the plan" and "a fatal error", both of which this app legitimately writes.
    (r"\bfatal (?:accident|injury|illness|crash|fall|mishap)\b", "death"),
    # Person-anchored nouns. "life"/"passing"/"end" all have ordinary
    # non-mortal uses here, so each needs a person in the same sentence.
    (r"\b" + _DEATH_NOUN_REF + r"\b" + _SAME_SENTENCE +
     r"\b(?:short|brief|curtailed|limited) life\b", "death"),
    (r"\b" + _DEATH_NOUN_REF + r"\b" + _SAME_SENTENCE +
     r"\b(?:untimely|premature|sudden|early) (?:end|passing)\b", "death"),
    # Reverse order — "a short life is indicated for your son". The file
    # already handles both directions for immigration; this row was one-way.
    (r"\b(?:short|brief|curtailed) life\b" + _SAME_SENTENCE + r"\bfor "
     + _DEATH_NOUN_REF + r"\b", "death"),
    # "short-lived" and "life cut short" — the standard English renderings of
    # alpayu, the classical short-longevity class, and therefore the single
    # most likely phrasing in this app's own subject matter. Both were missed.
    # These two also accept a possessive pronoun ("his life will be cut
    # short"), which _DEATH_NOUN_REF deliberately excludes elsewhere. Safe
    # only because the predicate is unambiguous: nothing but a person's life
    # is described as "short-lived" or "cut short" in a reading, so the
    # anchor is carrying less weight here than it is on the "end" row.
    (r"\b" + _DEATH_NOUN_REF_POSS + r"\b" + _SAME_SENTENCE +
     r"\bshort[- ]lived\b", "death"),
    (r"\b" + _DEATH_NOUN_REF_POSS + r"\b" + _SAME_SENTENCE +
     r"\blife\b" + _SAME_SENTENCE + r"\bcut short\b", "death"),
    # Possessive noun forms: "your father's demise is indicated". The verb
    # equivalent was caught and this was not.
    (r"\byour (?:" + _THIRD_PARTY_SUBJECTS + r")(?:'s|s')" + _SAME_SENTENCE +
     r"\b(?:death|demise|passing)\b", "death"),
    # Pronoun + lifespan noun: "his lifespan will be short".
    (r"\b(?:his|her|their)\b" + _SAME_SENTENCE +
     r"\b(?:lifespan|life span|life expectancy|longevity)\b" + _SAME_SENTENCE +
     r"\b(?:short|limited|brief|curtailed|reduced)\b", "death"),
    # Explicit noun list rather than "\w+ years": the wildcard read
    # "teenage years", "retirement years" and "golden years" as death.
    (r"\b" + _DEATH_NOUN_REF + r"\b" + _SAME_SENTENCE +
     r"\bwill not (?:see|reach|live to see|make it to)\b" + _SAME_SENTENCE +
     r"\b(?:old age|adulthood|maturity|\d+)\b", "death"),
    (r"\byou (?:will|are likely to) live (?:until|to|for)\b", "death"),
    # NOTE ON THIS MERGE: the row that stood here —
    #   (r"\byou have\b.{0,24}\b(?:years|months) (?:left|to live)\b", "death")
    # — is deliberately DELETED, not kept alongside the replacement below.
    # It is superseded, and resolving this conflict by keeping both sides
    # restores a demonstrated false positive: it reads "you have 2 years left
    # in this Saturn dasha" as a death verdict and swaps an ordinary reading
    # for the longevity refer-out. "left"/"remaining" are what a dasha
    # legitimately has and are handled by the windowed check further down.

    # "N years/months TO LIVE" is absolute — no period-noun window check —
    # because unlike "remaining"/"left" it has no ordinary astrological
    # meaning. Nobody describes a dasha as having "6 months to live", so a
    # nearby "dasha" cannot launder it: "your grandmother has 6 months to live
    # in this Saturn dasha" is the same verdict as the sentence without the
    # clause. "left" and "remaining" deliberately do NOT appear here — they
    # are what a period legitimately has, and they stay in the windowed check
    # below. Getting that split wrong in the other direction is a real,
    # demonstrated bug: the pre-existing `you have ... years left` line this
    # replaces flagged "you have 2 years left in this Saturn dasha" as a death
    # verdict, which would have replaced an ordinary reading with the
    # longevity refer-out.
    (_HAS_SUBJECT + _ADVERB_GAP + r"\b(?:" + _DURATION_COUNT + r")\s*(?:years?|months?)\s*to live\b", "death"),
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
    # 2026-08-09 (foreign domain review, three rounds): output-side mirror
    # of the immigration input-gate above. Rounds 1-2 progressively fixed
    # the vocabulary; round 3 found the *scaffolding* around it — the
    # future-framing words and the adverb gap — was still copy-pasted per
    # arm and had drifted the identical way the vocabulary once did: arm 2
    # (the "you will VERB SUBJECT" active-voice form) had no framing
    # alternation or adverb gap at all, so "you will definitely get your
    # green card" and "you are going to get your green card" both slipped
    # through even though "you will get" alone was caught. Both arms now
    # share `_FUTURE_FRAMING`/`_ADVERB_GAP` with the input-side pattern
    # above (well, would if the input gate needed future-framing — it
    # doesn't, `seeks_verdict` already covers that separately; the sharing
    # here is between this file's two output arms).
    (r"\b(?:your |the )?(?:" + _IMMIGRATION_SUBJECTS + r")s?\b" + _ADVERB_GAP +
     r"\b(?:" + _FUTURE_FRAMING + r")\b" + _ADVERB_GAP +
     r"\b(?:be )?(?:" + _IMMIGRATION_OUTCOME_VERBS + r")\b", "legal"),
    (r"\byou (?:" + _FUTURE_FRAMING + r")\b" + _ADVERB_GAP +
     r"\b(?:be )?(?:" + _IMMIGRATION_OUTCOME_VERBS + r")\b.{0,24}"
     r"\b(?:your |the )?(?:" + _IMMIGRATION_SUBJECTS + r")s?\b", "legal"),
    (r"\byou (?:" + _FUTURE_FRAMING + r")\b" + _ADVERB_GAP + r"\b(?:be )?deport(?:ed)?\b", "legal"),
    (r"\byou (?:will|are going to) face deportation\b", "legal"),
    (r"\bdeportation is (?:certain|guaranteed|inevitable|going to happen)\b", "legal"),
    # A different sentence shape from the two arms above: the outcome is a
    # NOUN fused into the subject phrase itself ("your green card approval
    # is guaranteed") rather than a verb following the subject, so there's
    # no separate outcome word after "is guaranteed" for the first arm's
    # pattern to find.
    # The outcome word here is optional, not required — a fourth review
    # found "your green card approval is guaranteed" was caught but "your
    # green card is guaranteed" (no outcome noun at all, the certainty
    # word alone carries the whole claim) was not, an asymmetry visible in
    # the deportation mirror right above it having exactly this shape
    # already ("deportation is certain", no separate outcome word needed).
    # A fifth review found "highly likely"/"near certain" are the exact
    # same claim as "certain"/"guaranteed" here, just hedged in wording —
    # "your visa approval is highly likely" carries the same false
    # precision as "your visa approval is guaranteed".
    (r"\b(?:your |the )?(?:" + _IMMIGRATION_SUBJECTS + r")s?(?:\s+(?:" + _IMMIGRATION_OUTCOME_VERBS + r"))?\b"
     r".{0,16}\bis (?:certain|guaranteed|inevitable|a certainty|"
     r"highly likely|very likely|extremely likely|near certain|almost certain)\b", "legal"),
    # A fifth review found "odds are excellent" — a different certainty
    # construction the two arms above don't cover, since the certainty
    # adjective follows "odds are"/"odds of", not "is".
    (r"\b(?:your |the )?(?:" + _IMMIGRATION_SUBJECTS + r")s?(?:\s+(?:" + _IMMIGRATION_OUTCOME_VERBS + r"))?\b"
     r".{0,16}\bodds (?:are|of)\b.{0,16}\b(?:excellent|good|high|strong|favou?rable|in your favou?r)\b", "legal"),
    # A fifth review found a quantified-probability sentence — "the
    # probability of your visa being approved is 90%" — entirely
    # uncaught, since none of the arms above expect the subject and
    # outcome to be introduced by a leading "probability of" clause.
    (r"\bprobability of\b.{0,40}\b(?:" + _IMMIGRATION_SUBJECTS + r")s?\b.{0,40}"
     r"\b(?:" + _IMMIGRATION_OUTCOME_VERBS + r")\b.{0,30}\b\d{1,3}\s*%", "legal"),
    (r"\byou (?:will|should|ought to) (?:buy|sell|invest in|purchase)\b.{0,24}\b(?:stock|share|crypto|mutual funds?)\b", "money"),
    (r"\b(?:purchase|buy|sell|invest in)\b.{0,20}\b(?:stocks?|shares?|crypto|holdings|mutual funds?)\b.{0,25}\b(?:now|immediately|today)\b", "money"),
    # 2026-08-10 (personality domain, independent-review round 1): the
    # personality addendum explicitly prohibits clinical/psychiatric/
    # diagnostic vocabulary ("no 'disorder,' 'pathology,' 'dysfunction,'
    # 'diagnosis'"), but that was prompt-only — nothing on the output side
    # checked it, confirmed by two independent reviewers with identical
    # probes ("consistent with a mild anxiety disorder", "narcissistic
    # tendency", "astrologically diagnostic of a borderline personality
    # pattern", "cognitive distortions", "avoidant attachment style" all
    # passed clean). Health-kind, not a new category: an undisclosed
    # clinical/psychological assessment is exactly what health's refer-out
    # boundary already exists to keep this app from doing, regardless of
    # which domain's agent produced it. Bare vocabulary match, not a
    # sentence shape — these terms have no legitimate use in this app's
    # output (a chart-based tendency is never phrased as a diagnosis), so
    # the false-positive risk of matching them anywhere in an answer is low.
    (r"\b(?:personality|mental|psychiatric|anxiety|mood|panic|bipolar|obsessive-compulsive) disorders?\b", "health"),
    (r"\bborderline personality\b", "health"),
    (r"\bnarcissistic (?:tendenc\w+|traits?|personality|disorder)\b", "health"),
    (r"\battachment style\b", "health"),
    (r"\bcognitive distortions?\b", "health"),
    (r"\bpsychopatholog\w+\b", "health"),
    (r"\bclinically (?:diagnos\w+|significant)\b", "health"),
    (r"\bsymptoms? of (?:a |an )?(?:mental|psychological|personality)\b", "health"),
    (r"\bdiagnos(?:tic|ed|is)\b.{0,20}\b(?:personality|character|temperament)\b", "health"),
    (r"\b(?:personality|character|temperament)\b.{0,20}\bdiagnos(?:tic|ed|is)\b", "health"),
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
# 2026-08-10: third-party subjects added here for the same reason as in the
# death cluster above — "your mother has 3 years left" is the identical verdict
# to "you have 3 years left" and was equally uncaught. The period-noun window
# below still does the real work: "your father has 3 years remaining in his
# Saturn dasha" is ordinary period language and stays clean, exactly as the
# first-person version of that sentence already did.
#
# 2026-08-11 (review H2): "to live" was removed from this alternation and made
# an absolute pattern in `_PROHIBITED_OUTPUT` instead. It never belonged here.
# This check exists to spare sentences where a nearby period noun proves the
# duration describes a DASHA — and "6 months to live" is never a dasha, so the
# window could only ever launder a real verdict ("your grandmother has 6 months
# to live in this Saturn dasha" was cleared by it). What is left here is
# exactly the vocabulary a period legitimately uses.
_YEARS_MONTHS_REMAINING = re.compile(
    r"\b(?:you have|your (?:" + _THIRD_PARTY_SUBJECTS + r")(?:'s|s')? has|he has|she has|they have)\b"
    r".{0,20}\b(?:" + _DURATION_COUNT + r")\s*(?:years?|months?)\s*(?:remaining|left|to go)\b"
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
    # ("fated", "barren", "blocked by...alignment") that check doesn't
    # cover, and is specific/rare enough not to need generalizing into that
    # machinery. Kept here (not in the negation-checked wealth/children
    # tuple below) genuinely because it's domain-agnostic — no wealth or
    # children noun in the pattern itself, unlike its siblings a sixth
    # review found misplaced (see that tuple).
    # Excludes bare "end" — a dasha/transit period legitimately "ends" all
    # the time ("this dasha is fated to end in March" would be ordinary
    # period language, not fatalism), found by review.
    r"\bfated to (?:dissolve|fail|collapse)\b",
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
    # Moved here from the marriage/poetic tuple by a sixth review: these
    # three actually name a wealth or children noun (poverty/childlessness/
    # womb/fertility/birth), so they have the exact same "does not mean
    # [phrase]" literal-substring problem the rest of this tuple exists to
    # handle — sitting in the bare-`re.search` tuple meant they had no
    # negation awareness even though their semantics needed it. Demonstrated
    # concretely: "This dosha does not mean poverty is your inescapable
    # destiny" was flagged before this move.
    r"\bsentenced (?:you|your \w+) to (?:struggle|hardship|poverty|childlessness|failure)\b",
    r"\b(?:womb|fertility) is (?:cosmically |permanently )?barren\b",
    r"\bbirth is blocked by\b",
    r"\bis your inescapable destiny\b",
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

# Negative character-trait vocabulary shared by the sentence-shape patterns
# below. One constant, not copied per pattern — the immigration-vocabulary
# constants earlier in this file drifted between copies exactly this way.
#
# 2026-08-09/10 (personality domain build, independent-review round 1):
# an 8-adjective enumeration ("selfish, arrogant, dishonest, cruel,
# weak-willed, manipulative, cold, untrustworthy") missed everyday negative
# traits entirely — "you will always be lazy/jealous/greedy" all passed
# clean, confirmed by two independent reviewers. Widened substantially
# rather than left closed; still an explicit list (not a bare `\w+`
# wildcard) because "you will always be X" genuinely needs X to be a
# negative trait to be a violation at all — "you will always be loved" or
# "you will always be capable of growth" use the identical sentence shape
# non-fatalistically, and a wildcard would flag those too. A closed list is
# the safer trade here; this one is wide enough that the round-1 review's
# own adversarial misses (lazy, jealous, greedy, envious) are all covered,
# plus the neighboring vocabulary that same review's phrasing style implies.
_PERSONALITY_NEGATIVE_TRAITS = (
    r"selfish|arrogant|dishonest|cruel|weak-willed|manipulative|cold|untrustworthy|"
    r"lazy|jealous|greedy|envious|petty|cowardly|reckless|impulsive|controlling|"
    r"deceitful|vindictive|spiteful|possessive|aggressive|unreliable|irresponsible|"
    r"immature|shallow|vain|heartless|unfeeling|unkind|rude|disrespectful|"
    r"untrusting|distant|aloof|withdrawn|closed-off|insecure|needy|"
    r"jealousy|greed|envy|pettiness|dishonesty|cruelty|selfishness|arrogance"
)
# Trait-neutral fatalistic sentence *shapes* — these carry the same absolute,
# unfalsifiable claim regardless of which trait word (if any) fills the
# slot, so unlike the vocabulary-anchored patterns above these don't need an
# enumerated word list to stay safe. Added the same round for the same
# reason: independent review found the original list was anchored to fixed
# phrase *shapes* as much as fixed *vocabulary*, and a plausible paraphrase
# defeated it by changing either one. "Once a manipulator, always a
# manipulator" generalizes via a backreference (any repeated noun in that
# construction is fatalism by construction, not just the reviewed example);
# the others are specific enough idioms that a bare `re.search` carries low
# false-positive risk the same way the rest of this file's explicit-phrase
# patterns do.
_PERSONALITY_FATALISM_SHAPES = (
    r"\bonce a (\w+), always a \1\b",
    r"\byou will always struggle with \w+(?:\s\w+){0,2}\b",
    r"\bthis is your unchangeable core\b",
    r"\bno remedy can (?:ever )?soften this\b",
    r"\brewiring is not on the table\b",
    r"\bthis chart proves it will never change\b",
    r"\bbaked into (?:your chart|you) (?:permanently|and cannot be undone)\b",
    r"\bthis (?:yoga|dosha|placement) locks in a difficult character that no remedy can (?:ever )?soften\b",
    r"\bnothing will move that needle\b",
)

# 2026-08-09 (personality domain build). Same category as the wealth/children
# tuple above and checked the same way (`_negation_precedes`, not a bare
# `re.search`) for the identical reason: the personality domain addendum
# explicitly instructs the model to hedge trait descriptions ("this does not
# mean you will always be selfish" is exactly the reassurance shape the
# addendum asks for), so these phrases will routinely appear as a literal
# substring of an actually-safe sentence. Explicit phrase matching, not a
# generic fatalism-verb x character-trait-noun cross product — that
# generic-windowing mechanism was tried for wealth/children in rounds 1-2,
# found to have real, repeated bugs (missing negation, over-wide clause
# splitting, a verb that disqualified its own match), and abandoned in favor
# of this exact style. Character fatalism is CLAUDE.md's dosha-is-a-flag
# principle applied to personality traits: a challenging placement is a flag
# to describe, never grounds for telling someone their character is fixed,
# broken, or beyond change.
_PERSONALITY_OVERCLAIM_OUTPUT = (
    r"\byou will always be (?:" + _PERSONALITY_NEGATIVE_TRAITS + r")\b",
    r"\byou can never change (?:who you are|your nature|your character|your personality)\b",
    r"\bthis (?:placement|dosha|yoga) means you can never trust anyone\b",
    r"\byour character is (?:fixed|broken) and cannot change\b",
    r"\byou are permanently flawed\b",
    r"\byou are destined to (?:always be|remain) (?:" + _PERSONALITY_NEGATIVE_TRAITS + r")\b",
    r"\byou will never overcome this weakness\b",
    r"\byour personality cannot be changed\b",
    r"\byou are incapable of change\b",
    r"\bthis is simply who you are and nothing can change it\b",
    r"\byou are fundamentally flawed\b",
    r"\b(?:guarantees?|dictates?) a (?:bad|flawed|broken) character\b",
    r"\bcondemned to a life of (?:" + _PERSONALITY_NEGATIVE_TRAITS + r")\b",
    r"\bcursed with this personality\b",
    r"\byou cannot help being (?:selfish|manipulative|dishonest|cruel)\b",
    r"\byour nature will never change\b",
    r"\bthere is no changing who you are\b",
    r"\byou are stuck with this (?:flaw|weakness|character) forever\b",
    r"\byou will never (?:trust|connect with|open up to) anyone\b",
    r"\bthis dosha means you are (?:a bad person|inherently flawed|beyond change)\b",
    r"\byour flaws are permanent and unfixable\b",
    r"\byou are trapped by your own character\b",
    r"\bno amount of effort will change who you are\b",
    r"\byou(?:'re| are) wired this way and rewiring is not on the table\b",
    r"\bfrankly, you are just a\b.{0,15}\bperson and this chart proves it will never change\b",
    r"\bcannot be undone\b.{0,30}\b(?:your character|your nature|this flaw|this weakness)\b",
    *_PERSONALITY_FATALISM_SHAPES,
)

# 2026-08-12 (Codex review of PR #45, health-deepen integration prep): the
# health-deepen pass reframes accident/injury susceptibility as a caution —
# "this configuration indicates a tendency toward accidents" — exactly the
# same flag-not-verdict standard as a dosha. Nothing previously stopped the
# model from crossing that line into a definite future event ("you will
# have an accident"), which is a different claim: not a chart-derived
# tendency, but a specific outcome prediction — the thing CLAUDE.md's health
# non-negotiable exists to prevent, just phrased around "accident"/"surgery"
# rather than the disease/diagnosis vocabulary the refer-out gate already
# covers. Checked with the negation check (`_negation_precedes`), same
# reason as wealth/children/personality above: "this does not mean you will
# have an accident" is exactly the reassurance shape a caution-framed answer
# is expected to use, and contains the bad phrase as a literal substring.
_HEALTH_OUTCOME_OVERCLAIM_OUTPUT = (
    r"\byou will (?:have|get|meet with|suffer) an? (?:accident|injury)\b",
    r"\ban accident will happen(?: to you)?\b",
    r"\byou (?:will|are going to) (?:be|get) (?:injured|hurt)\b",
    r"\byou will (?:need|require) surgery\b",
    r"\byou (?:will|are going to) end up in (?:the |a )?hospital\b",
    r"\bthis (?:combination|configuration|placement) guarantees an accident\b",
    r"\ban accident is (?:certain|inevitable)\b",
    r"\bsurgery is (?:certain|inevitable)\b",
    r"\byou cannot avoid (?:this accident|getting injured|needing surgery)\b",
    r"\byou are certain to (?:have an accident|get injured|need surgery)\b",
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
    # 2026-08-10 (personality domain, independent-review round 2): "it
    # would be wrong to say X" is the same hedge shape as "wrongly claim
    # X"/"is false that X" already above, just phrased as an editorializing
    # lead-in rather than a claim-verb — found missing by review, the
    # identical category of gap (a new phrasing of an already-covered
    # hedge, not a new hedge concept) as every prior addition to this list.
    r"wrong to say|"
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
#
# A sixth review pointed out this bias is monotone-safe (proof, not a
# sampling result): adding a boundary character can only shrink the
# backward-search window, so it can only make `_negation_precedes` return
# True *less* often, never more — i.e. it can only flag more, never less.
# That means widening this set is always safe to do outright, with no
# trade-off to weigh, unlike the comma/conjunction question above. The
# review found three real gaps that were exactly this — not the accepted
# comma-ambiguity limitation, but genuine coverage holes in the *unsafe*
# direction: bare conjunctions with no comma ("remedies cannot help and
# this dosha guarantees poverty"), parentheses ("this dosha does not
# affect your health (it guarantees poverty)"), and bullet/newline-joined
# lines (`_normalize()` collapses `\n` to a space, so a hedge on one
# bullet line silently covers a violation on the next). Closed for free.
_CLAUSE_BOUNDARY = re.compile(
    r"[.;:!?,()*]|—|–|--|\s-\s|\band\b|\bbut\b|\bso\b|\bbecause\b"
)


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
    substring — a problem marriage's patterns don't have. Personality
    patterns (`_PERSONALITY_OVERCLAIM_OUTPUT`) need the same negation check
    and for the same reason as wealth/children: the personality domain
    addendum explicitly instructs hedged framing ("this does not mean you
    will always be selfish"), so the reassurance form is expected, common
    output, not an edge case. Health outcome patterns
    (`_HEALTH_OUTCOME_OVERCLAIM_OUTPUT`) need it for the identical reason: a
    caution-framed answer is expected to say "this does not mean you will
    have an accident" as reassurance."""
    normalized = _normalize(answer)
    for pattern in _DOSHA_OVERCLAIM_OUTPUT:
        if re.search(pattern, normalized):
            return "dosha_overclaim"
    for pattern in (*_WEALTH_CHILDREN_OVERCLAIM_OUTPUT, *_PERSONALITY_OVERCLAIM_OUTPUT):
        for match in re.finditer(pattern, normalized):
            if not _negation_precedes(normalized, match.start()):
                return "dosha_overclaim"
    for pattern in _HEALTH_OUTCOME_OVERCLAIM_OUTPUT:
        for match in re.finditer(pattern, normalized):
            if not _negation_precedes(normalized, match.start()):
                return "health_outcome_overclaim"
    return None
