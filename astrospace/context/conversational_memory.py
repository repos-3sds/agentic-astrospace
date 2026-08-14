"""Deterministic, assertion-only candidates for reader-controlled memory."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryCandidate:
    key: str
    value: dict
    label: str
    display_value: str
    sensitivity: str
    excerpt: str

    @property
    def requires_confirmation(self) -> bool:
        return self.sensitivity in {"sensitive", "highly_sensitive"}

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "value": self.value,
            "label": self.label,
            "display_value": self.display_value,
            "sensitivity": self.sensitivity,
            "excerpt": self.excerpt,
            "requires_confirmation": self.requires_confirmation,
        }


# Automatic memory must begin from a positive assertion, not an expanding
# collection of ways a sentence might be hypothetical or secondhand. We only
# inspect sentence clauses that START as a first-person declarative statement.
# This accepts "I am retired" and "For context, I work as a teacher", while
# excluding "I wonder whether I am retired" and "My chart indicates I am
# retired" before their later `I am ...` fragments are even considered.
_ASSERTION_START = re.compile(
    r"^\s*(?:(?:for context|to clarify|just so you know)\s*[:,]?\s+)?"
    r"(?:i\s+(?:am|have been|work as|am employed as|have)\b|i\s*['’]m\b)",
    re.I,
)
_SENTENCE_BREAK = re.compile(r"(?<=[.!?;])\s+")

# Anywhere in the message, not just at the start — "Suppose I am retired,
# what would the chart say?" and "What happens if I am married?" both put
# the hypothetical marker mid-sentence, after where `_QUESTION_OPEN`'s
# start-anchored check already gave up. Reproduced as real false positives
# in review (PR #66): both were extracted as if the reader had actually
# asserted retired/married. Precision matters far more than recall here —
# in automatic mode a false positive silently writes a wrong fact to the
# active profile, where a false negative just means the reader adds it
# manually later — so this deliberately over-suppresses rather than trying
# to scope the check to only the clause containing the hypothetical.
_HYPOTHETICAL_RE = re.compile(
    r"\bif\b|\bsuppos(?:e|ing)\b|\bimagin(?:e|ing)\b|\bhypothetical(?:ly)?\b|"
    r"\bassuming\b|\bin case\b|\blet'?s say\b|\bpretend(?:ing)?\b",
    re.I,
)
# Reported/quoted speech and reported BELIEF — "My mother said 'I am
# retired now.'" is the mother's own statement, not the reader's; "They
# believe I am retired." / "According to my mother, I am retired." /
# "My friend thinks I am married." / "My wife insists I am retired." are
# all someone ELSE's claim ABOUT the reader, not the reader's own
# assertion, even though grammatically "I am retired" still appears as
# the embedded clause. `_THIRD_PERSON` alone misses all of these because
# it only matches a third-person subject directly followed by
# is/am/are/has/have/works — a reporting or belief verb, or an
# "according to" attribution, sits between them instead. Straight and
# curly double quotes catch quoted material generally; single quotes are
# deliberately excluded since they collide with contractions ("I'm") too
# often to use as a reliable signal.
_REPORTED_SPEECH_RE = re.compile(
    r'["“”]|\baccording to\b|\b(?:said|says?|told|tells?|mention(?:ed|s)?|'
    r"claim(?:ed|s)?|stat(?:ed|es)?|wrote|writes?|texted|messaged|"
    r"believe[sd]?|think[s]?|thought|insist(?:s|ed)?|heard)\b",
    re.I,
)

_CODE_PATTERNS = (
    ("employment_status", "retired", "Work status", "Retired", r"\bi(?:'m| am| have been) retired\b"),
    ("employment_status", "self_employed", "Work status", "Self-employed", r"\bi(?:'m| am) self[- ]employed\b"),
    ("employment_status", "unemployed", "Work status", "Not currently working", r"\bi(?:'m| am) (?:unemployed|not currently working)\b"),
    ("employment_status", "student", "Work status", "Student", r"\bi(?:'m| am) (?:a )?student\b"),
    ("relationship_status", "married", "Relationship", "Married", r"\bi(?:'m| am| have been) married\b"),
    ("relationship_status", "divorced", "Relationship", "Divorced", r"\bi(?:'m| am) divorced\b"),
    ("relationship_status", "separated", "Relationship", "Separated", r"\bi(?:'m| am) separated\b"),
    ("relationship_status", "widowed", "Relationship", "Widowed", r"\bi(?:'m| am) widowed\b"),
    ("relationship_status", "single", "Relationship", "Single", r"\bi(?:'m| am) single\b"),
)
_OCCUPATION = re.compile(r"\bi (?:work as|am employed as|am an?|['’]m an?)\s+([a-z][a-z .&/-]{1,60})", re.I)
_CHILDREN = re.compile(
    r"\bi have\s+(?:(?:\d{1,2}|one|two|three|four|five|six)\s+)?"
    r"(?:children|kids|sons?|daughters?)\b", re.I,
)


def extract_memory_candidates(text: str) -> list[MemoryCandidate]:
    """Return only explicit first-person assertions from one user turn."""
    clean = " ".join(text.strip().split())
    if (not clean or _HYPOTHETICAL_RE.search(clean)
            or _REPORTED_SPEECH_RE.search(clean)):
        return []
    found: list[MemoryCandidate] = []
    for sentence in _SENTENCE_BREAK.split(clean):
        if not _ASSERTION_START.match(sentence):
            continue
        for key, code, label, display, pattern in _CODE_PATTERNS:
            match = re.search(pattern, sentence, re.I)
            if match:
                sensitivity = "sensitive" if key == "relationship_status" else "personal"
                found.append(MemoryCandidate(key, {"code": code}, label, display, sensitivity, match.group(0)))
        child = _CHILDREN.search(sentence)
        if child:
            found.append(MemoryCandidate("has_children", {"value": True}, "Children", "Has children", "sensitive", child.group(0)))
        occupation = _OCCUPATION.search(sentence)
        if occupation:
            value = occupation.group(1).strip(" .")
            # Avoid absorbing a second clause into the occupation value.
            value = re.split(r"\b(?:and|but|because|who)\b", value, maxsplit=1, flags=re.I)[0].strip()
            value = re.sub(r"^(?:a|an)\s+", "", value, flags=re.I)
            if value.lower() not in {"student", "retired", "unemployed", "married", "single"}:
                found.append(MemoryCandidate("occupation", {"text": value}, "Occupation", value, "personal", occupation.group(0)))
    deduped: dict[str, MemoryCandidate] = {}
    for candidate in found:
        deduped[candidate.key] = candidate
    return list(deduped.values())
