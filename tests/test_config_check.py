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


def test_prerender_audio_takes_on_without_a_warning():
    from astrospace.config import flag
    assert check_environment({"DAILY_BRIEF_PRERENDER_AUDIO": "on"}) == []
    assert flag("DAILY_BRIEF_PRERENDER_AUDIO", {"DAILY_BRIEF_PRERENDER_AUDIO": "on"}) is True


def test_flag_and_integer_keep_the_old_rules():
    from astrospace.config import flag, integer
    assert flag("ASTROSPACE_QUOTAS_ENFORCED", {"ASTROSPACE_QUOTAS_ENFORCED": "1"}) is True
    assert flag("ASTROSPACE_QUOTAS_ENFORCED", {"ASTROSPACE_QUOTAS_ENFORCED": "on"}) is False
    assert flag("ASTROSPACE_QUOTAS_ENFORCED", {}) is False
    assert flag("DAILY_BRIEF_AGENT", {}) is True
    assert flag("DAILY_BRIEF_AGENT", {"DAILY_BRIEF_AGENT": "off"}) is False
    assert integer("DB_POOL_SIZE", 5, {"DB_POOL_SIZE": "ten"}) == 5
    assert integer("DB_POOL_SIZE", 5, {"DB_POOL_SIZE": "8"}) == 8


def test_flags_and_numbers_are_read_only_through_config():
    """A module parsing a flag on its own is how the two rules drifted."""
    import re
    from pathlib import Path
    from astrospace.config import VARS
    names = [var.name for var in VARS if var.kind in ("opt_in", "opt_out", "int")]
    pattern = re.compile(r"(getenv|environ\.get|environ\[)\(?\s*\"(" + "|".join(names) + r")\"")
    root = Path(__file__).resolve().parents[1]
    offenders = [str(path.relative_to(root)) for path in (root / "astrospace").rglob("*.py")
                 if path.name != "config.py" and pattern.search(path.read_text())]
    assert offenders == []
