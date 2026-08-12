"""JsonKnowledgeBase.retrieve()'s require_subdomain_match filter.

Isolated from the real references.json via a small fixture store, so these
tests pin down the filter's exact behavior rather than depending on however
many references the real KB happens to have for a given subdomain today."""
import json

import pytest

from astrospace.context.kb import JsonKnowledgeBase

_STORE = {
    "references": [
        {
            "ref_id": "h1", "domains": ["health"], "subdomains": ["accidents_surgery"],
            "statement": "Mars afflicted indicates injury-proneness.",
            "source": {"text_key": "bphs", "location": "17.11"}, "status": "verified_common",
        },
        {
            "ref_id": "h2", "domains": ["health"], "subdomains": ["accidents_surgery"],
            "statement": "8th lord in lagna: general wound vulnerability.",
            "source": {"text_key": "bphs", "location": "24.85"}, "status": "verified_common",
        },
        {
            "ref_id": "h3", "domains": ["health"], "subdomains": ["chronic_disease"],
            "statement": "Saturn affliction: constitutional windy-type sensitivity.",
            "source": {"text_key": "bphs", "location": "17.10"}, "status": "verified_common",
        },
        {
            "ref_id": "h4", "domains": ["health"], "subdomains": ["vitality"],
            "statement": "Jupiter well-placed protects against illness.",
            "source": {"text_key": "bphs", "location": "17.9"}, "status": "verified_common",
        },
        {
            "ref_id": "c1", "domains": ["career"], "subdomains": ["promotion_authority"],
            "statement": "10th lord exalted: honour and authority.",
            "source": {"text_key": "bphs", "location": "21.2"}, "status": "verified_common",
        },
    ],
}


@pytest.fixture()
def kb(tmp_path):
    path = tmp_path / "references.json"
    path.write_text(json.dumps(_STORE))
    return JsonKnowledgeBase(references_path=path)


def test_default_behavior_unchanged_returns_every_domain_match(kb):
    """No new argument passed at all — must match pre-existing behavior
    exactly: subdomains only rank, never exclude."""
    refs = kb.retrieve(["health"], subdomains=["accidents_surgery"], limit=20)
    assert {r.ref_id for r in refs} == {"h1", "h2", "h3", "h4"}


def test_require_subdomain_match_false_is_the_default_and_ranks_only(kb):
    refs = kb.retrieve(["health"], subdomains=["accidents_surgery"], limit=20,
                        require_subdomain_match=False)
    assert {r.ref_id for r in refs} == {"h1", "h2", "h3", "h4"}
    # still ranked so the matching pair comes first, non-matches trail
    assert {r.ref_id for r in refs[:2]} == {"h1", "h2"}


def test_require_subdomain_match_true_excludes_non_matching_refs(kb):
    refs = kb.retrieve(["health"], subdomains=["accidents_surgery"], limit=20,
                        require_subdomain_match=True)
    assert {r.ref_id for r in refs} == {"h1", "h2"}


def test_require_subdomain_match_true_with_empty_subdomains_does_not_filter(kb):
    """The narrowing caller's safety contract: an empty subdomain set (a
    classifier miss) must never turn into an all-exclude filter."""
    refs = kb.retrieve(["health"], subdomains=[], limit=20,
                        require_subdomain_match=True)
    assert {r.ref_id for r in refs} == {"h1", "h2", "h3", "h4"}


def test_domain_filter_is_still_a_hard_filter_regardless(kb):
    refs = kb.retrieve(["career"], subdomains=["accidents_surgery"], limit=20,
                        require_subdomain_match=True)
    assert {r.ref_id for r in refs} == set()
    refs2 = kb.retrieve(["career"], subdomains=[], limit=20)
    assert {r.ref_id for r in refs2} == {"c1"}


def test_require_subdomain_match_true_narrows_below_the_limit(kb):
    """The real-world case this exists for: the domain has more references
    than the requested subdomain covers, and limit alone (today's only
    lever) can't express 'only the on-topic ones' when limit >= total."""
    refs = kb.retrieve(["health"], subdomains=["accidents_surgery"], limit=30,
                        require_subdomain_match=True)
    assert len(refs) == 2
    assert len(refs) < len(_STORE["references"])
