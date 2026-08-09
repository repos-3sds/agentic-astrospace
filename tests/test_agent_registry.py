"""Registry holds only configured/runnable agents, not all 10 taxonomy
domains — a routed domain absent here must fall out to `domain_not_ready`,
never a fallback answer. See astrospace/agents/registry.py."""
from astrospace.agents.registry import AGENT_REGISTRY, AgentConfig
from astrospace.context.taxonomy import domain_ids, get_domain


class TestAgentRegistry:
    def test_only_career_marriage_and_wealth_are_configured(self):
        assert set(AGENT_REGISTRY) == {"career", "marriage", "wealth"}

    def test_configured_domains_are_real_taxonomy_domains(self):
        for domain_id in AGENT_REGISTRY:
            assert domain_id in domain_ids()

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

    def test_unconfigured_taxonomy_domains_still_have_display_names(self):
        """domain_not_ready needs a real display name for any of the other
        8 domains — via taxonomy directly, not a placeholder registry row."""
        unconfigured = set(domain_ids()) - set(AGENT_REGISTRY)
        assert unconfigured  # sanity: there really are unconfigured domains
        for domain_id in unconfigured:
            assert get_domain(domain_id).name
