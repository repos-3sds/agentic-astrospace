"""Which Ask engine a reader gets.

ASK_ENGINE   bundle (default) | agent
    bundle: today's Ask for everyone except the accounts in ASK_AGENT_EMAILS.
    agent:  the tool-using Ask (agents/explorer.py) for everyone.
ASK_AGENT_EMAILS   comma-separated accounts that get the tool-using Ask while
    ASK_ENGINE is bundle. Unset means the owner's account only, so the
    prototype can be tried in production without any env change; set it to
    an empty string to turn it off for everyone.
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
