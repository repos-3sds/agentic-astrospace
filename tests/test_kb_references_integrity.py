"""Invariants on the reference store itself.

The KB is the one place where a rule the product refuses to answer could enter
the system as ordinary retrievable content. `safety.py` nets the model's OUTPUT;
nothing until now checked what we hand the model as INPUT. A longevity rule
retrieved into a bundle is an invitation the output guard then has to refuse,
and relying on that is a worse design than never retrieving it.
"""
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from astrospace.context import assembler as assembler_module
from astrospace.context.kb import get_knowledge_base

REFS_PATH = Path("astrospace/context/references.json")
SOURCES_PATH = Path("astrospace/context/sources.json")


@pytest.fixture(scope="module")
def store() -> dict:
    return json.loads(REFS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def references(store) -> list[dict]:
    return store["references"]


# Phrases that would make a reference a longevity or mortality claim. Deliberately
# broader than safety.py's output patterns: this is about what may be STORED, and
# a store is cheap to keep clean, so the bar is "does not discuss lifespan" rather
# than "does not phrase a verdict".
_MORTAL = re.compile(
    r"\b(death|dies?|dying|died|mortality|maraka|"
    r"longevity|lifespan|life ?span|short-lived|long-lived|"
    r"will not survive|end of life|fatal|"
    # A lifespan can be asserted without any of the words above — "gives a span
    # of twenty to thirty-two years" is BPHS ch.19 v.8 and named no vocabulary
    # this pattern originally held. Found by running the guard against the
    # rules that were deliberately NOT ingested, rather than only against the
    # ones that were.
    r"span of|years of life|will live|(long|short|brief|full) life|"
    # Same discovery, different chapter: BPHS ch.16's child-loss shlokas
    # ("the native will ... lose his child", "loss of children at 33 and 36",
    # "grief on account of loss of child", "3 will pass away") describe a
    # child's death without any word above. A guard that only ever gets tested
    # against a book's LONGEVITY chapter will not catch a different chapter's
    # death phrasing — it has to be tested against every closed chapter, not
    # just the first one that taught the lesson. Brought forward from the
    # children/foreign PR (#39) since this branch predates it.
    r"lose (?:his|her|their|a) child(?:ren)?|loss of (?:a |his |her |their )?child(?:ren)?|"
    r"pass(?:ed)? away|will pass away|"
    # "demise" is a word this project's OWN safety.py death-noun work (the
    # third-party guard) was built to catch in model output ("your father's
    # demise is indicated in 2031") — and it was absent from THIS guard the
    # whole time. Found via the Phaladeepika cross-check pass, testing the
    # guard against a third book's phrasing rather than assuming two books
    # had exhausted the vocabulary.
    r"demise)\b",
    re.I,
)


def test_no_reference_asserts_longevity_or_death(references):
    """CLAUDE.md refers longevity out to a professional. BPHS carries a great
    deal of it — ch.19, ch.43, ch.44, the arishta chapters, and three rows of
    ch.48's dasha list — and extracting it was deliberate. Retrieving it is not.

    If this fails, someone ingested a chapter that was closed on purpose. The
    fix is to remove the reference, not to soften its wording."""
    offenders = []
    for ref in references:
        text = f"{ref['statement']} {ref.get('observance_note', '')}"
        hit = _MORTAL.search(text)
        if hit:
            offenders.append((ref["ref_id"], hit.group(0)))
    assert not offenders, (
        "references must not carry longevity/mortality claims — "
        f"found {offenders}"
    )


def test_ref_ids_are_unique(references):
    ids = [r["ref_id"] for r in references]
    dupes = {i for i in ids if ids.count(i) > 1}
    assert not dupes, f"duplicate ref_ids would make citations ambiguous: {dupes}"


def test_every_source_is_in_the_curated_catalogue(references):
    """A citation to a text we have not vetted is worse than no citation."""
    catalogue = set(json.loads(SOURCES_PATH.read_text(encoding="utf-8"))["sources"])
    unknown = {r["source"]["text_key"] for r in references} - catalogue
    assert not unknown, f"references cite sources absent from sources.json: {unknown}"


def test_convention_dependent_references_explain_themselves(references):
    """CLAUDE.md: anything convention-dependent states the rule used. A flag with
    no note tells a reader something is disputed without telling them how."""
    missing = [r["ref_id"] for r in references
               if r.get("status") == "convention_dependent"
               and not r.get("observance_note")
               and r["ref_id"].startswith("bphs")
               and "p." in r["source"]["location"]]
    assert not missing, (
        "convention_dependent references added from a verifiable source must "
        f"carry an observance_note: {missing}"
    )


def test_verse_level_citations_name_their_translation(references):
    """Chapter numbers differ between editions — Sharma's ch.19 is Santhanam's
    ch.17, the same chapter. A bare 'ch.17' is ambiguous across the corpus, so
    any location precise enough to carry a verse must name the translation."""
    unnamed = [r["ref_id"] for r in references
               if re.search(r"\bv{1,2}\.\d", r["source"]["location"])
               and "trans." not in r["source"]["location"]]
    assert not unnamed, f"verse-level citations must name the translation: {unnamed}"


@pytest.mark.parametrize("domain", ["career", "health", "wealth"])
def test_the_new_rules_are_actually_retrievable(domain):
    """The point of the exercise: extracts that sit in a markdown file change
    nothing. These must come back through the real retrieval path."""
    retrieved = {r.ref_id for r in get_knowledge_base().retrieve([domain])}
    from_bphs_verse_level = {r for r in retrieved if re.match(r"bphs\d", r)}
    assert from_bphs_verse_level, (
        f"{domain} retrieves no verse-level BPHS reference — the KB extracts are "
        "not wired into retrieval"
    )


def test_retrieval_reaches_the_cross_domain_dasha_rules():
    """The drekkana emphasis rule is what makes a long period readable. It is
    registered against several domains, so a regression that dropped multi-domain
    references would silently remove it everywhere at once."""
    for domain in ("career", "health", "wealth"):
        ids = {r.ref_id for r in get_knowledge_base().retrieve([domain])}
        assert "bphs47_3_drekkana_emphasis" in ids, domain


# Health-caution content (2026-08-12) is a deliberately new class: it names a
# body system or a life-stage as worth attending to, but never the specific
# disease and never the literal age those combinations were softened FROM.
# The point of these two checks is drift, not the initial write — a future
# edit that "clarifies" a caution by naming what it's actually about is
# exactly how this class of content quietly turns back into the verdict it
# was built not to be.
_NAMED_DIAGNOSIS = re.compile(
    r"\b(leprosy|cancer|tumou?r|tuberculosis|consumption|diabetes|epilepsy|"
    r"syphilis|smallpox|jaundice|dysentery|hepatitis|asthma|arthritis)\b",
    re.I,
)


def test_health_caution_references_do_not_name_a_disease(references):
    """The whole point of the caution reframe is a body-system or life-stage
    flag, never the specific diagnosis. If this fails, a caution has drifted
    back into the verdict it was built to avoid."""
    offenders = [(r["ref_id"], _NAMED_DIAGNOSIS.search(r["statement"]).group(0))
                 for r in references
                 if r["ref_id"].startswith("bphs17_") and _NAMED_DIAGNOSIS.search(r["statement"])]
    assert not offenders, f"health caution references name a specific disease: {offenders}"


_LITERAL_AGE = re.compile(r"\bage(?:d|s)?\s+\d{1,3}\b|\bat\s+\d{1,3}\b|\byears?\s+of\s+age\b", re.I)


def test_vigilance_period_references_do_not_state_a_literal_age(references):
    """The vigilance-period rows were built specifically by stripping the
    source verse's literal ages (6, 12, 19, 22, 26, 29, 30, 45, 59) down to a
    life-stage bucket (childhood/youth/midlife). A literal age creeping back
    in here is the same failure the marriage and children timing corrections
    exist to prevent, one chapter later."""
    offenders = [(r["ref_id"], _LITERAL_AGE.search(r["statement"]).group(0))
                 for r in references
                 if r["ref_id"].startswith("bphs17_vigilance_periods_")
                 and _LITERAL_AGE.search(r["statement"])]
    assert not offenders, f"vigilance-period references state a literal age: {offenders}"


# Brought forward from the marriage PR (#38) since this branch predates it.
TAXONOMY_PATH = Path("astrospace/context/taxonomy.json")


def _taxonomy_subdomains() -> dict[str, set[str]]:
    raw = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    domains = raw["domains"] if isinstance(raw, dict) and "domains" in raw else raw
    items = domains.items() if isinstance(domains, dict) else ((d["id"], d) for d in domains)
    out: dict[str, set[str]] = {}
    for domain_id, spec in items:
        subs = spec.get("subdomains", [])
        out[domain_id] = {s if isinstance(s, str) else s.get("id") for s in subs}
    return out


def test_every_domain_named_by_a_reference_exists(references):
    known = set(_taxonomy_subdomains())
    unknown = {d for r in references for d in r["domains"]} - known
    assert not unknown, f"references target domains absent from taxonomy.json: {unknown}"


def test_every_subdomain_named_by_a_reference_exists(references):
    """A reference filed under a subdomain that does not exist is unreachable —
    retrieval by that subdomain returns nothing, and no error is raised anywhere.

    This test exists because it happened: the marriage rules were first written
    against `marital_harmony`, which is not in the taxonomy (the real id is
    `harmony_discord`). Everything passed. The rules were simply invisible to a
    subdomain-scoped query, which is the failure this whole file is meant to
    make loud."""
    taxonomy = _taxonomy_subdomains()
    bad: list[str] = []
    for ref in references:
        for sub in ref.get("subdomains") or []:
            # A subdomain is valid if ANY of the reference's domains declares it.
            if not any(sub in taxonomy.get(domain, set()) for domain in ref["domains"]):
                bad.append(f"{ref['ref_id']}:{sub}")
    assert not bad, f"references filed under subdomains no domain declares: {bad}"


def test_no_domains_bundle_reference_count_exceeds_kb_limit(references):
    """assemble_domain()'s kb_limit caps how many references kb.retrieve()
    can return. If any single domain's real reference count grows past that
    cap, references silently stop reaching the model — correctly written,
    correctly cited in the KB, and invisible to a reading anyway, with
    nothing failing loudly to say so. This is a general-case guard, not tied
    to any one domain's content, so it keeps working as the KB grows."""
    kb_limit = assembler_module.assemble_domain.__kwdefaults__["kb_limit"]
    counts = Counter(
        domain for ref in references for domain in ref.get("domains", [])
    )
    worst_domain, worst_count = counts.most_common(1)[0]
    assert worst_count <= kb_limit, (
        f"{worst_domain!r} has {worst_count} references, exceeding kb_limit "
        f"({kb_limit}) — raise kb_limit or this domain's references will be "
        f"silently truncated before reaching the model"
    )
