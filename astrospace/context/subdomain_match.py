"""Question-aware subdomain narrowing — cheap heuristic, never model-generated.

Same discipline as `astrospace/agents/intent.py`: a regex table checked
against the question text, no LLM call. `assemble_domain()` uses this to ask
`kb.retrieve()` for only the references that actually bear on the question,
instead of every reference the domain has (see `assembler.py`'s call site).

A miss is always safe: `match_subdomains()` returns an empty set when nothing
matches, and the caller's contract is to fall back to the domain's full
subdomain list with `require_subdomain_match=False` — exactly today's
behavior. Narrowing only ever activates on a confident match.

**Scope, deliberately narrow.** Patterns exist for `health`, `career`,
`marriage`, `children`, `wealth` only — the five domains with a real KB
extraction pass behind them (see
`docs/health_kb_bphs_susceptibility_and_injury.md`,
`docs/career_kb_bphs_10th_house.md`, `docs/marriage_kb_bphs_7th_house.md`,
`docs/children_kb_bphs_5th_house.md`,
`docs/wealth_kb_bphs_2nd_11th_house.md`), where the subdomain vocabulary is
grounded in the source text rather than guessed. The remaining six taxonomy
domains (`education`, `family_property`, `foreign`, `spirituality`,
`litigation`, `personality`) currently carry only a handful of references
each and have had no equivalent extraction pass — writing keyword tables
for them now would be guessing English phrasing for subdomains with no
grounding to check it against. `match_subdomains()` returns an empty set
for any domain not in `_PATTERNS`, which is exactly the safe no-op the
empty-match contract already handles — so adding a domain here later is
additive, not a redesign.

`wealth`'s table covers only `income`, `losses` and `poverty_combinations`
— the three subdomains the ch.13/ch.22/ch.24 extraction actually grounds
(see that doc's "What this pass does not cover"). `savings`, `speculation`,
`inheritance` and `debts` have no pattern rows; a question naming them
falls through to the safe no-narrow default like any other miss, until a
future pass grounds them too.

Each subdomain listed here is a real entry in `taxonomy.json`'s domain spec;
`test_subdomain_match.py::test_every_pattern_key_is_a_real_subdomain` guards
that these tables can't drift from the taxonomy silently.
"""
from __future__ import annotations

import re

_PATTERNS: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "career": (
        ("job_vs_business", (r"\bjob\b", r"\bbusiness\b", r"\bemploy", r"\bself[- ]employ", r"\bstart(?:ing)? (?:a |my )?(?:own )?business\b")),
        ("promotion_authority", (r"\bpromot", r"\braise\b", r"\bauthority\b", r"\bmanager\b", r"\blead(?:ership)?\b")),
        ("field_selection", (r"\bfield\b", r"\bwhich career\b", r"\bwhat career\b", r"\bindustry\b")),
        ("job_change", (r"\bchange (?:my |a )?job\b", r"\bswitch(?:ing)? job", r"\bnew job\b", r"\bresign")),
        ("unemployment", (r"\bunemploy", r"\bjobless\b", r"\bfired\b", r"\blaid off\b", r"\blose my job\b")),
        ("government_politics", (r"\bgovernment\b", r"\bpolitic", r"\bcivil service\b", r"\belection\b")),
        ("fame_status", (r"\bfame\b", r"\bfamous\b", r"\breputation\b", r"\bstatus\b", r"\brecognition\b")),
    ),
    "marriage": (
        ("timing_of_marriage", (r"\bwhen (?:will|would) i (?:get )?marr", r"\bmarriage timing\b", r"\bhow soon.{0,10}marr")),
        ("spouse_nature", (r"\bspouse\b", r"\bpartner('s)? nature\b", r"\bwhat.{0,10}spouse.{0,10}like\b")),
        ("harmony_discord", (r"\bharmony\b", r"\bdiscord\b", r"\bfight", r"\bconflict\b", r"\bget along\b")),
        ("compatibility", (r"\bcompatib", r"\bmatch(?:ing)?\b.{0,10}marriage\b", r"\bkundli match")),
        ("delay_denial", (r"\bdelay(?:ed)? marriage\b", r"\bwhy (?:haven't|am i not) i marr", r"\bno marriage\b")),
        ("second_marriage", (r"\bsecond marriage\b", r"\bremarr")),
        ("divorce", (r"\bdivorce\b", r"\bseparat(?:e|ion)\b", r"\bmarriage end")),
        ("romance", (r"\bromance\b", r"\blove life\b", r"\bdating\b")),
    ),
    "health": (
        ("vitality", (r"\bvitality\b", r"\benergy levels?\b", r"\bstamina\b", r"\boverall health\b")),
        ("chronic_disease", (r"\bchronic\b", r"\blong[- ]term (?:illness|disease|condition)\b", r"\bconstitution\b")),
        ("acute_disease", (r"\bfever\b", r"\binfection\b", r"\bsudden illness\b", r"\bsick(?:ness)?\b")),
        ("mental_health", (r"\bstress\b", r"\banxiety\b", r"\bmental health\b", r"\bmental well", r"\bmind\b")),
        ("accidents_surgery", (r"\baccident\b", r"\bsurgery\b", r"\bwound\b", r"\binjur", r"\boperation\b")),
        ("recovery", (r"\brecover(?:y|ing)?\b", r"\bheal(?:ing)?\b")),
        ("hospitalization", (r"\bhospital", r"\badmit(?:ted)?\b")),
    ),
    "children": (
        ("timing_of_children", (r"\bwhen will i have (?:a )?child", r"\bhave kids\b", r"\bchild(?:ren)? timing\b")),
        ("delay_difficulty", (r"\bdelay.{0,15}child", r"\bdifficulty.{0,15}(?:conceiv|child)", r"\btrouble.{0,10}conceiv")),
        ("child_wellbeing", (r"\bchild(?:'s|ren'?s)? (?:health|wellbeing|well-being)\b",)),
        ("relationship_with_children", (r"\brelationship with (?:my )?child", r"\bbond with (?:my )?child")),
        ("adoption", (r"\badopt",)),
    ),
    "wealth": (
        ("income", (r"\bincome\b", r"\bsalary\b", r"\bearn(?:ing)?s?\b", r"\bmoney (?:coming|come) in\b", r"\bgains?\b")),
        ("losses", (r"\bfinancial loss(?:es)?\b", r"\blose money\b", r"\blosing money\b", r"\bexpenditure\b", r"\bexpenses?\b")),
        ("poverty_combinations", (r"\bpoverty\b", r"\bstruggl(?:e|ing) financially\b", r"\bnever have (?:enough )?money\b", r"\bfinancial(?:ly)? strain\b")),
    ),
}


def match_subdomains(question: str | None, domain_id: str) -> set[str]:
    """Regex-match `question` against `domain_id`'s subdomain patterns.

    Returns an empty set on no match, an unrecognized/ungrounded domain, or
    an empty question — the caller's contract is that an empty result means
    "don't narrow", never "match nothing"."""
    if not question:
        return set()
    normalized = " ".join(question.casefold().split())
    patterns = _PATTERNS.get(domain_id, ())
    return {
        subdomain for subdomain, regexes in patterns
        if any(re.search(regex, normalized) for regex in regexes)
    }
