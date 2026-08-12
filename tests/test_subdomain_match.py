"""Question-aware subdomain narrowing — one case per grounded domain, plus
the safe-fallback contract. See astrospace/context/subdomain_match.py."""
import pytest

from astrospace.context.subdomain_match import _PATTERNS, match_subdomains
from astrospace.context.taxonomy import get_domain


@pytest.mark.parametrize(("question", "domain_id", "expected"), [
    ("Will I have an accident or need surgery?", "health", {"accidents_surgery"}),
    ("How is my overall vitality and energy levels?", "health", {"vitality"}),
    ("Am I prone to any chronic illness?", "health", {"chronic_disease"}),
    ("Will I recover quickly after this operation?", "health", {"accidents_surgery", "recovery"}),
    ("When will I get married?", "marriage", {"timing_of_marriage"}),
    ("Will there be a lot of conflict and fighting in my marriage?", "marriage", {"harmony_discord"}),
    ("Am I heading for a divorce?", "marriage", {"divorce"}),
    ("Should I take this job offer or start my own business?", "career", {"job_vs_business"}),
    ("Will I get a promotion soon?", "career", {"promotion_authority", "timing_of_marriage"} & {"promotion_authority"}),
    ("When will I have children?", "children", {"timing_of_children"}),
    ("Are we having difficulty conceiving?", "children", {"delay_difficulty"}),
    ("Should we adopt?", "children", {"adoption"}),
])
def test_match_subdomains_confident_hits(question, domain_id, expected):
    assert match_subdomains(question, domain_id) == expected


@pytest.mark.parametrize("question", [
    "Tell me about my chart",
    "What does the 10th house mean?",
    "Give me a general reading",
])
def test_vague_questions_match_nothing(question):
    """A miss must be an empty set, not a guess — this is the fallback
    contract assemble_domain() relies on to know when *not* to filter."""
    assert match_subdomains(question, "health") == set()
    assert match_subdomains(question, "career") == set()


def test_empty_question_matches_nothing():
    assert match_subdomains("", "health") == set()
    assert match_subdomains(None, "health") == set()


def test_unrecognized_domain_matches_nothing():
    """Domains with no pattern table (no extraction pass behind them yet)
    must degrade to the same safe empty-set fallback as a vague question,
    never raise."""
    assert match_subdomains("Will I travel abroad?", "foreign") == set()
    assert match_subdomains("Am I spiritual?", "spirituality") == set()


def test_case_insensitive():
    assert match_subdomains("WILL I HAVE AN ACCIDENT", "health") == {"accidents_surgery"}


@pytest.mark.parametrize("domain_id", list(_PATTERNS.keys()))
def test_every_pattern_key_is_a_real_subdomain(domain_id):
    """Guards against the table drifting from taxonomy.json — a typo'd or
    renamed subdomain here would silently narrow to nothing forever."""
    real_subdomains = set(get_domain(domain_id).subdomains)
    for subdomain, _patterns in _PATTERNS[domain_id]:
        assert subdomain in real_subdomains, (
            f"{domain_id!r} pattern table references {subdomain!r}, "
            f"which is not one of {domain_id!r}'s real subdomains"
        )


@pytest.mark.parametrize(("domain_id", "subdomain"), [
    (domain_id, subdomain)
    for domain_id, entries in _PATTERNS.items()
    for subdomain, _patterns in entries
])
def test_every_pattern_group_is_a_real_tuple_not_a_bare_string(domain_id, subdomain):
    """Caught during this PR's own build: `("adoption", (r"\\badopt")),` is
    missing a trailing comma, so `(r"\\badopt")` is just a parenthesized
    string, not a 1-tuple — `for regex in regexes` then iterates over
    individual characters of the pattern and raises `re.error` on the first
    question that reaches it. A wrong type here fails loudly at runtime
    only when a real question happens to hit that subdomain, so it's worth
    a direct, no-question-needed check instead of relying on that."""
    patterns = dict(_PATTERNS[domain_id])[subdomain]
    assert isinstance(patterns, tuple), (
        f"{domain_id}.{subdomain}'s pattern group is a {type(patterns).__name__}, "
        f"not a tuple — likely a missing trailing comma"
    )


@pytest.mark.parametrize("domain_id", list(_PATTERNS.keys()))
def test_every_real_subdomain_has_at_least_a_pattern_or_is_intentionally_absent(domain_id):
    """Not a hard requirement (some subdomains genuinely lack distinctive
    phrasing), but every grounded domain's pattern table must cover most of
    its subdomains — otherwise narrowing barely does anything for that
    domain and the table isn't earning its place in _PATTERNS."""
    real_subdomains = set(get_domain(domain_id).subdomains)
    covered = {subdomain for subdomain, _ in _PATTERNS[domain_id]}
    assert len(covered) >= len(real_subdomains) * 0.5
