"""Registry holds only configured/runnable agents. All 11 taxonomy domains
are configured as of 2026-09-04 (education, family_property, and litigation
were the last three) — a domain routed here that somehow isn't registered
(a future 12th taxonomy domain, or a bug) must still fall out to
`domain_not_ready`, never a fallback answer; see
test_domain_agent.py::TestAskOrchestratorPrepare::test_unsupported_domain_is_not_ready
for that mechanism proven directly, since there's no longer a naturally-
unsupported real domain to exercise it against. See astrospace/agents/registry.py."""
from astrospace.agents.registry import AGENT_REGISTRY, AgentConfig
from astrospace.context.taxonomy import domain_ids, get_domain


class TestAgentRegistry:
    def test_only_configured_domains_are_present(self):
        assert set(AGENT_REGISTRY) == {
            "career", "marriage", "wealth", "children", "health", "foreign",
            "personality", "spirituality", "education", "family_property",
            "litigation",
        }

    def test_configured_domains_are_real_taxonomy_domains(self):
        for domain_id in AGENT_REGISTRY:
            assert domain_id in domain_ids()

    def test_every_taxonomy_domain_is_now_configured(self):
        """All 11 taxonomy domains are live as of 2026-09-04 — confirmed
        directly against taxonomy.py rather than a hardcoded count, so this
        stays true if a domain's taxonomy spec changes without anyone
        remembering to update this file too."""
        assert set(AGENT_REGISTRY) == set(domain_ids())

    def test_each_config_has_a_real_addendum(self):
        for config in AGENT_REGISTRY.values():
            assert isinstance(config, AgentConfig)
            assert config.domain_addendum.strip()

    def test_marriage_addendum_names_manglik_dosha_explicitly(self):
        """The sensitive-domain guardrail acceptance criterion: marriage's
        framing must name manglik dosha and its flag-not-verdict handling,
        not just say "dosha" generically."""
        addendum = AGENT_REGISTRY["marriage"].domain_addendum.lower()
        assert "manglik" in addendum
        assert "never" in addendum  # the explicit prohibitions

    def test_every_configured_domain_has_a_real_display_name(self):
        """`domain_not_ready` (for any domain that ever falls out of
        AGENT_REGISTRY, now or in the future) reads its display name
        straight from taxonomy.py, never a placeholder — confirmed here for
        every domain actually configured today."""
        for domain_id in AGENT_REGISTRY:
            assert get_domain(domain_id).name

    def test_personality_addendum_names_the_trait_not_verdict_framing(self):
        """The sensitive-domain guardrail acceptance criterion for this
        domain: it must explicitly say traits are chart-based tendencies,
        not fixed verdicts on someone's character, and must rule out
        clinical/psychiatric vocabulary — not just say "be careful"."""
        addendum = AGENT_REGISTRY["personality"].domain_addendum.lower()
        assert "tendency" in addendum or "tendencies" in addendum
        assert "never" in addendum
        assert "clinical" in addendum or "psychiatric" in addendum
        assert "verdict" in addendum

    def test_spirituality_addendum_names_the_key_guardrails(self):
        """The sensitive-domain guardrail acceptance criterion for this
        domain: it must explicitly forbid directing a reader to renounce or
        leave a real relationship/career, forbid confirming or denying a
        real person's status as a guru, and forbid asserting a specific
        past-life claim as settled fact — not just say "be careful"."""
        addendum = AGENT_REGISTRY["spirituality"].domain_addendum.lower()
        assert "never" in addendum
        assert "renounce" in addendum
        assert "guru" in addendum
        assert "past-life" in addendum or "past life" in addendum
        assert "guru chandala" in addendum
        assert "kemadruma" in addendum

    def test_education_addendum_names_the_key_guardrails(self):
        """Must explicitly forbid predicting a specific exam result/grade as
        certain, forbid clinical/diagnostic vocabulary for intelligence or
        learning difficulty, and frame a break/setback as a flag rather than
        a verdict on capability."""
        addendum = AGENT_REGISTRY["education"].domain_addendum.lower()
        assert "never" in addendum
        assert "pass" in addendum and "fail" in addendum
        assert "disability" in addendum or "disorder" in addendum
        assert "verdict" in addendum

    def test_family_property_addendum_names_the_key_guardrails(self):
        """Must explicitly name the father's-house convention as genuinely
        layered rather than settled, forbid directive real-estate/investment
        advice, and hold the same reader-decides boundary on domestic/
        relocation questions."""
        addendum = AGENT_REGISTRY["family_property"].domain_addendum.lower()
        assert "never" in addendum
        assert "father" in addendum
        assert "9th house" in addendum and "10th house" in addendum
        assert "real-estate" in addendum or "real estate" in addendum or "investment" in addendum
        assert "reader decides" in addendum

    def test_litigation_addendum_names_the_key_guardrails(self):
        """Must explicitly state the advisory-tone-only convention flag,
        forbid predicting a specific case outcome/sentence/imprisonment, and
        forbid confirming or denying guilt or innocence in a real dispute."""
        addendum = AGENT_REGISTRY["litigation"].domain_addendum.lower()
        assert "never" in addendum
        assert "advisory tone only" in addendum
        assert "verdict" in addendum
        assert "guilt" in addendum or "innocence" in addendum
        assert "imprisonment" in addendum
