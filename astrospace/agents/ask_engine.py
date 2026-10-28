"""Which Ask engine a reader gets.

ASK_ENGINE   bundle (default) | agent
    bundle: today's Ask for everyone except the accounts in ASK_AGENT_EMAILS.
    agent:  the tool-using Ask (agents/explorer.py) for everyone.
ASK_AGENT_EMAILS   comma-separated accounts that get the tool-using Ask while
    ASK_ENGINE is bundle. Unset means the owner's account only, so the
    prototype can be tried in production without any env change; set it to
    an empty string to turn it off for everyone.

A reader who has the tool-using Ask can get today's Ask for one question by
starting it with "/old ", to compare the two on the same question.
"""
from __future__ import annotations

import os

OWNER_EMAILS = "vikramadityavss@gmail.com"


def uses_agent(email: str | None) -> bool:
    if os.getenv("ASK_ENGINE", "bundle").strip().lower() == "agent":
        return True
    allowed = {
        value.strip().lower()
        for value in os.getenv("ASK_AGENT_EMAILS", OWNER_EMAILS).split(",")
        if value.strip()
    }
    return bool(email) and email.strip().lower() in allowed


OLD_PREFIX = "/old "


def choose_engine(email: str | None, question: str) -> tuple[bool, str]:
    """(explore, question): whether this turn uses the tool-using Ask, and
    the question with any "/old " comparison prefix removed."""
    explore = uses_agent(email)
    if explore and question.lower().startswith(OLD_PREFIX):
        return False, question[len(OLD_PREFIX):].lstrip()
    return explore, question
