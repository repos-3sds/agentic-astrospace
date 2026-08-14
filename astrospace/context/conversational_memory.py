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


_QUESTION_OPEN = re.compile(r"^\s*(?:when|will|would|could|can|should|do|does|did|am i|are we|is my)\b", re.I)
_THIRD_PERSON = re.compile(r"\b(?:my (?:mother|father|wife|husband|partner|son|daughter|child)|he|she|they)\s+(?:is|am|are|has|have|works?)\b", re.I)

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
    if not clean or _QUESTION_OPEN.search(clean) or _THIRD_PERSON.search(clean):
        return []
    found: list[MemoryCandidate] = []
    for key, code, label, display, pattern in _CODE_PATTERNS:
        match = re.search(pattern, clean, re.I)
        if match:
            sensitivity = "sensitive" if key == "relationship_status" else "personal"
            found.append(MemoryCandidate(key, {"code": code}, label, display, sensitivity, match.group(0)))
    child = _CHILDREN.search(clean)
    if child:
        found.append(MemoryCandidate("has_children", {"value": True}, "Children", "Has children", "sensitive", child.group(0)))
    occupation = _OCCUPATION.search(clean)
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
