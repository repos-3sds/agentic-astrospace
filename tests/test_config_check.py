"""The boot-time environment check (audit I9): warn, never refuse."""
from astrospace.config import check_environment


def test_a_clean_environment_has_no_problems():
    assert check_environment({"ASTROSPACE_QUOTAS_ENFORCED": "1", "DAILY_BRIEF_AGENT": "off",
                              "DB_POOL_SIZE": "5", "OWNER_ALERT_EMAILS": "a@b.co, c@d.in"}) == []


def test_on_for_an_opt_in_flag_is_called_out_as_off():
    problems = check_environment({"ASTROSPACE_QUOTAS_ENFORCED": "on"})
    assert problems == ["ASTROSPACE_QUOTAS_ENFORCED=on reads as OFF (this flag is on only for 1, true or yes)"]


def test_typos_numbers_and_lists():
    problems = check_environment({
        "REVENUECAT_ACCEPT_SANDBOX": "ture",
        "DB_POOL_SIZE": "ten",
        "DAILY_BRIEF_LOOKAHEAD": "10pm",
        "ADMIN_EMAILS": "me@x.com,not-an-email",
        "ASTROSPACE_LIMIT_ASK_PER_DAY": "lots",
        "AI_PROVIDER": "openai",
    })
    assert len(problems) == 6


def test_text_values_are_never_echoed():
    problems = check_environment({"GEMINI_API_KEY": " sk-secret-value\n"})
    assert problems == ["GEMINI_API_KEY has spaces or a newline around it"]
    assert "secret" not in problems[0]


def test_cloud_run_needs_its_database_and_keys():
    problems = check_environment({"K_SERVICE": "agentic-astrospace"})
    assert "neither DATABASE_URL nor SUPABASE_DB_URL is set on Cloud Run" in problems
    assert "GEMINI_API_KEY is not set on Cloud Run" in problems


def test_never_raises_on_odd_input():
    assert isinstance(check_environment({"DAILY_BRIEF_AGENT": "", "PORT": "-1"}), list)
