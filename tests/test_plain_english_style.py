"""Every reader-facing English prompt carries the one shared style rule, and
Telugu keeps its own instruction (agents/style.py)."""
from astrospace.agents import daily_brief_agent, domain_agent, period_agent, qa_agent, validation_agent
from astrospace.agents.style import PLAIN_INDIAN_ENGLISH


def test_every_english_prompt_uses_the_shared_rule():
    for prompt in (
        daily_brief_agent.SYSTEM,
        period_agent.PERIOD_SYSTEM,
        domain_agent.LANGUAGE_INSTRUCTIONS["en"],
        validation_agent._SYSTEM,
        qa_agent.QA_SYSTEM,
    ):
        assert PLAIN_INDIAN_ENGLISH in prompt


def test_telugu_instruction_is_unchanged_by_the_english_rule():
    assert PLAIN_INDIAN_ENGLISH not in domain_agent.LANGUAGE_INSTRUCTIONS["te"]


def test_rule_survives_str_format():
    # domain and validation prompts are .format()-ed; a brace would break them.
    assert "{" not in PLAIN_INDIAN_ENGLISH and "}" not in PLAIN_INDIAN_ENGLISH
