"""KeywordRouter's ranked_domains — the raw ranking the Ask orchestrator
reads to decide "is this a genuine tie" without recomputing scoring
itself. See astrospace/context/router.py and
AskOrchestrator._needs_clarification's docstring."""
from astrospace.context.router import KeywordRouter


class TestRankedDomains:
    def test_single_clean_match_has_no_close_second(self):
        decision = KeywordRouter().route("Will I get a promotion soon?")
        assert decision.confidence == "medium"
        assert decision.ranked_domains[0][0] == "career"
        # No second domain scored, or it's not within one hit — a clean
        # single-keyword match, not a tie.
        if len(decision.ranked_domains) > 1:
            assert decision.ranked_domains[0][1] - decision.ranked_domains[1][1] > 1

    def test_genuinely_ambiguous_question_ties(self):
        decision = KeywordRouter().route("Is this a good time for my career and my marriage?")
        assert decision.confidence == "medium"
        top_two = decision.ranked_domains[:2]
        domains = {d for d, _, _ in top_two}
        assert domains == {"career", "marriage"}
        assert top_two[0][1] - top_two[1][1] <= 1

    def test_matched_terms_are_carried_per_domain(self):
        decision = KeywordRouter().route("Will I settle abroad after marriage?")
        by_domain = {domain: terms for domain, _, terms in decision.ranked_domains}
        assert "marriage" in by_domain["marriage"]
        assert "foreign" in by_domain or "abroad" in by_domain.get("foreign", ())

    def test_zero_match_has_empty_ranked_domains(self):
        decision = KeywordRouter().route("asdkfj qwerty nonsense")
        assert decision.confidence == "low"
        assert decision.ranked_domains == ()

    def test_high_confidence_two_keyword_hits(self):
        decision = KeywordRouter().route("Should I resign from my job and start a new business?")
        assert decision.confidence == "high"
        assert decision.ranked_domains[0][1] >= 2
