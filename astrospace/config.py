"""One list of the environment variables the server and worker read, checked
at boot (audit I9).

About sixty variables are read in some thirty modules, each with its own
parsing rule. Two rules for on/off flags live side by side: opt-in flags
(quotas, sandbox purchases, tester Plus) are on only for 1/true/yes, and
opt-out flags (the agents) are off only for off/0/false. So a value that
reads as "on" to a person can quietly mean off: ASTROSPACE_QUOTAS_ENFORCED=on
leaves quotas unenforced, and DB_POOL_SIZE=ten stops the server at import.

This module is warn-only on purpose. A fail-fast check could take Cloud Run
down over a variable that is optional today; the plan is to watch one deploy's
logs, fix what they show, and only then let the check refuse to boot. The
reads themselves still happen where they always did; moving them onto one
settings object is the second half of I9, in the deferred backlog.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Mapping

log = logging.getLogger(__name__)

OPT_IN = {"1", "true", "yes"}
OPT_OUT = {"off", "0", "false"}
# Words people type for a flag. Anything else in a flag is a typo.
FLAG_WORDS = OPT_IN | OPT_OUT | {"on", "no", ""}


@dataclass(frozen=True)
class Var:
    name: str
    # "opt_in": on only for 1/true/yes. "opt_out": off only for off/0/false.
    # "int", "hhmm", "url", "email_list", "choice", "text".
    kind: str = "text"
    choices: frozenset[str] = frozenset()
    # Expected to be set on the Cloud Run API service.
    cloud: bool = False
    # An opt-in flag that also takes "on" (DAILY_BRIEF_PRERENDER_AUDIO always has).
    accepts_on: bool = False


VARS: tuple[Var, ...] = (
    # Database and auth
    Var("DATABASE_URL", "url"),
    Var("SUPABASE_DB_URL", "url"),
    Var("SUPABASE_URL", "url", cloud=True),
    Var("SUPABASE_ANON_KEY", cloud=True),
    Var("SUPABASE_SERVICE_ROLE_KEY"),
    Var("SUPABASE_SECRET_KEY"),
    Var("SUPABASE_JWT_SECRET"),
    Var("DB_POOL_SIZE", "int"),
    Var("DB_MAX_OVERFLOW", "int"),
    Var("ASTROSPACE_CREATE_TABLES", "choice", frozenset({"1", "0", ""})),
    Var("ASTROSPACE_DEV_AUTH_BYPASS", "opt_in"),
    Var("ADMIN_EMAILS", "email_list"),
    Var("ALLOWED_ORIGINS"),
    Var("PUBLIC_BASE_URL", "url"),
    Var("PORT", "int"),
    # Plans and payments
    Var("ASTROSPACE_QUOTAS_ENFORCED", "opt_in"),
    Var("ASTROSPACE_TESTERS_GET_PLUS", "opt_in"),
    Var("ASTROSPACE_ENTITLEMENT_PROBES", "opt_in"),
    Var("REVENUECAT_ACCEPT_SANDBOX", "opt_in"),
    Var("REVENUECAT_SANDBOX_EMAILS", "email_list"),
    Var("REVENUECAT_WEBHOOK_AUTH"),
    Var("REVENUECAT_SECRET_API_KEY"),
    Var("RAZORPAY_KEY_ID"),
    Var("RAZORPAY_KEY_SECRET"),
    Var("RAZORPAY_WEBHOOK_SECRET"),
    Var("RAZORPAY_PLAN_IDS"),
    Var("RAZORPAY_ALLOWED_EMAILS", "email_list"),
    # Models
    Var("AI_PROVIDER", "choice", frozenset({"anthropic", "gemini", ""})),
    Var("GEMINI_BACKEND", "choice", frozenset({"vertex", "vertexai", "vertex_ai", "ai_studio", ""})),
    Var("GEMINI_API_KEY", cloud=True),
    Var("GEMINI_MODEL"),
    Var("ANTHROPIC_API_KEY"),
    Var("ANTHROPIC_MODEL"),
    Var("ASK_ENGINE", "choice", frozenset({"bundle", "agent", ""})),
    Var("ASK_AGENT_EMAILS", "email_list"),
    Var("ASK_SORTER", "choice", frozenset({"off", "heuristic", "0", "false", "ai", "on", "1", "true", ""})),
    Var("DAILY_BRIEF_AGENT", "opt_out"),
    Var("COMPAT_INSIGHT_AGENT", "opt_out"),
    Var("LIFE_STORY_AGENT", "opt_out"),
    # Worker, push, email, audio
    Var("DAILY_BRIEF_LOOKAHEAD", "hhmm"),
    Var("DAILY_BRIEF_PRERENDER_AUDIO", "opt_in", accepts_on=True),
    Var("ASTROSPACE_TTS_BUCKET"),
    Var("ASTROSPACE_TTS_PROJECT"),
    Var("ASTROSPACE_PUBLIC_AUDIO_BASE", "url"),
    Var("FCM_SERVICE_ACCOUNT_FILE"),
    Var("FCM_PROJECT_ID"),
    Var("RESEND_API_KEY"),
    Var("RESEND_WEBHOOK_SECRET"),
    Var("EMAIL_LINK_SECRET"),
    Var("EMAIL_FROM"),
    Var("EMAIL_REPLY_TO"),
    Var("EMAIL_POSTAL_ADDRESS"),
    Var("OWNER_ALERT_EMAILS", "email_list"),
    Var("RELEASE_CALLER"),
    Var("RELEASE_TOKEN_AUDIENCE", "url"),
    Var("LEGAL_OPERATOR_NAME"),
    Var("LEGAL_CONTACT_EMAIL"),
)

_EMAIL = re.compile(r"^[^@\s,]+@[^@\s,]+\.[^@\s,]+$")
_LIMIT = re.compile(r"^ASTROSPACE_LIMIT_[A-Z_]+_PER_(DAY|MINUTE)$")


def _problem(var: Var, raw: str) -> str | None:
    value = raw.strip()
    lowered = value.lower()
    if var.kind in ("opt_in", "opt_out"):
        if lowered not in FLAG_WORDS:
            return f"{var.name}={value!r} is not a flag value; use 1 or 0"
        if var.kind == "opt_in" and lowered == "on" and not var.accepts_on:
            return f"{var.name}=on reads as OFF (this flag is on only for 1, true or yes)"
        if var.kind == "opt_out" and lowered == "no":
            return f"{var.name}=no reads as ON (this flag is off only for off, 0 or false)"
    elif var.kind == "int":
        if value and not value.lstrip("-").isdigit():
            return f"{var.name}={value!r} is not a whole number"
    elif var.kind == "hhmm":
        if value and not re.fullmatch(r"\d{1,2}:\d{2}", value):
            return f"{var.name}={value!r} is not HH:MM; the default is used"
    elif var.kind == "url":
        if value and "://" not in value:
            return f"{var.name} does not look like a URL (no scheme)"
    elif var.kind == "email_list":
        bad = [part.strip() for part in value.split(",") if part.strip() and not _EMAIL.match(part.strip())]
        if bad:
            return f"{var.name} has {len(bad)} entr{'y' if len(bad) == 1 else 'ies'} that are not email addresses"
    elif var.kind == "choice":
        if lowered not in var.choices:
            return f"{var.name}={value!r} is not one of {sorted(c for c in var.choices if c)}"
    if value != raw:
        return f"{var.name} has spaces or a newline around it"
    return None


_BY_NAME = {var.name: var for var in VARS}


def flag(name: str, env: Mapping[str, str] | None = None) -> bool:
    """An on/off variable read by its one rule from VARS.

    Opt-in flags are on only for 1/true/yes (and "on" where the variable
    accepts it); opt-out flags are off only for off/0/false. Every module
    reads its flag through here, so the rule cannot differ by caller
    (tests/test_config_check.py holds that).
    """
    var = _BY_NAME[name]
    raw = ((os.environ if env is None else env).get(name) or "").strip().lower()
    if var.kind == "opt_in":
        return raw in OPT_IN or (var.accepts_on and raw == "on")
    if var.kind == "opt_out":
        return raw not in OPT_OUT
    raise KeyError(f"{name} is not a flag")


def integer(name: str, default: int, env: Mapping[str, str] | None = None) -> int:
    """A whole-number variable, or `default` when unset or not a number (the
    boot check has already logged the second case)."""
    if _BY_NAME[name].kind != "int":
        raise KeyError(f"{name} is not a number")
    raw = ((os.environ if env is None else env).get(name) or "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def check_environment(env: Mapping[str, str] | None = None) -> list[str]:
    """Plain-language problems with the environment; never raises.

    Values are never echoed for text variables, so a key pasted into the wrong
    variable cannot reach the logs through this check.
    """
    env = os.environ if env is None else env
    problems: list[str] = []
    for var in VARS:
        raw = env.get(var.name)
        if raw is None:
            continue
        if var.kind == "text":
            if raw != raw.strip():
                problems.append(f"{var.name} has spaces or a newline around it")
            continue
        found = _problem(var, raw)
        if found:
            problems.append(found)
    for name, raw in env.items():
        if _LIMIT.match(name) and not raw.strip().isdigit():
            problems.append(f"{name}={raw.strip()!r} is not a whole number; the default limit is used")
    # The API service (K_SERVICE) needs its sign-in and model keys; the
    # worker job (CLOUD_RUN_JOB) is deployed with a smaller set, so it is
    # only asked for a database.
    if env.get("K_SERVICE"):
        problems.extend(f"{var.name} is not set on Cloud Run" for var in VARS
                        if var.cloud and not (env.get(var.name) or "").strip())
    if (env.get("K_SERVICE") or env.get("CLOUD_RUN_JOB")) and not (
            env.get("DATABASE_URL") or env.get("SUPABASE_DB_URL")):
        problems.append("neither DATABASE_URL nor SUPABASE_DB_URL is set on Cloud Run")
    return problems


def log_environment_problems(env: Mapping[str, str] | None = None) -> list[str]:
    problems = check_environment(env)
    for problem in problems:
        log.warning("config: %s", problem)
    return problems
