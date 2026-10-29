"""Which saved profiles an Ask question is about.

Hawk, 2026-10-27: Ask uses the profiles the reader saved, with the
relationship the reader chose, and nothing else. So this is plain code, run
before any model sees the question: names and relationship words are matched
against the reader's own profiles, and a person the reader did not save is
reported as not saved rather than guessed at.

Relationships are the stored `kundlis.relation` values, normalised the way the
app's profile form does (ui/.../settings/profile-fields.ts), so "Mother" from
an older build and "parent" from the current one read the same.
"""
from __future__ import annotations

import re

MAX_PEOPLE = 5

# Stored relation, as the app normalises it.
_STORED = {
    "self": "self", "me": "self", "myself": "self",
    "spouse": "spouse", "wife": "spouse", "husband": "spouse",
    "partner": "partner",
    "child": "child", "son": "child", "daughter": "child",
    "parent": "parent", "mother": "parent", "father": "parent",
    "grandparent": "grandparent", "grandchild": "grandchild",
    "sibling": "sibling", "brother": "sibling", "sister": "sibling",
    "friend": "friend", "client": "client", "prospect": "prospect",
}
FAMILY = {"self", "spouse", "partner", "child", "parent", "grandparent", "grandchild",
          "sibling", "relative"}

# Words a reader uses -> the stored relation they point at.
_WORDS: dict[str, str] = {
    "wife": "spouse", "husband": "spouse", "spouse": "spouse", "hubby": "spouse",
    "partner": "partner", "fiance": "partner", "fiancee": "partner", "girlfriend": "partner",
    "boyfriend": "partner",
    "son": "child", "sons": "child", "daughter": "child", "daughters": "child",
    "child": "child", "children": "child", "kid": "child", "kids": "child",
    "mother": "parent", "mom": "parent", "mum": "parent", "amma": "parent",
    "father": "parent", "dad": "parent", "nanna": "parent", "appa": "parent",
    "parents": "parent", "in-laws": "parent",
    "brother": "sibling", "brothers": "sibling", "sister": "sibling", "sisters": "sibling",
    "sibling": "sibling", "siblings": "sibling", "anna": "sibling", "akka": "sibling",
    "tammudu": "sibling", "chelli": "sibling", "bhai": "sibling", "didi": "sibling",
    "grandmother": "grandparent", "grandfather": "grandparent", "grandma": "grandparent",
    "grandpa": "grandparent", "grandparents": "grandparent",
    "grandson": "grandchild", "granddaughter": "grandchild", "grandchildren": "grandchild",
    "friend": "friend", "friends": "friend",
}
_RELATION_RE = re.compile(r"\bmy\s+(?:\w+\s+)?(" + "|".join(
    sorted((re.escape(w) for w in _WORDS), key=len, reverse=True)) + r")\b")
# The reader taking part: "Lakshmi and I", "we", "our house", "both of us".
_SELF_RE = re.compile(r"\b(we|us|our|ours|both of us|all of us)\b"
                      r"|\b[a-z]+ and (i|me|myself)\b|\b(i|me) and [a-z]+")
_FAMILY_RE = re.compile(r"\b(whole family|our family|my family|entire family|all of us|"
                        r"everyone at home|family members|the family)\b")
_WORD = re.compile(r"[a-z]+")
# Words that already name more than one person.
_PLURAL = {"sons", "daughters", "children", "kids", "parents", "in-laws", "brothers",
           "sisters", "siblings", "grandparents", "grandchildren", "friends"}


def stored_relation(value: str | None) -> str:
    rel = (value or "").strip().lower()
    return _STORED.get(rel, "relative")


def resolve_people(question: str, profiles: list[dict], active_id: str,
                   picked_ids: list[str] | None = None) -> dict:
    """The people a question is about.

    ``profiles``: the reader's saved profiles as ``{"id", "name", "relation",
    "kind"}``. ``active_id``: the profile Ask is open on. ``picked_ids``:
    profiles the reader picked with "+" in the Ask box; they always count.

    Returns ``{"ids": [...], "group": bool, "not_saved": [words],
    "ambiguous": {word: [names]}, "whole_family": bool}``.
    ``ids`` puts the active profile first when it takes part; ``group`` is
    True when two or more people are involved.
    """
    text = (question or "").lower()
    by_id = {p["id"]: p for p in profiles}
    chosen: list[str] = []

    def add(pid: str) -> None:
        if pid in by_id and pid not in chosen:
            chosen.append(pid)

    for pid in picked_ids or []:
        add(pid)

    words = set(_WORD.findall(text))
    for p in profiles:
        first = (p.get("name") or "").split()
        if first and len(first[0]) >= 3 and first[0].lower() in words:
            add(p["id"])

    not_saved: list[str] = []
    ambiguous: dict[str, list[str]] = {}
    for match in _RELATION_RE.finditer(text):
        word = match.group(1)
        relation = _WORDS[word]
        hits = [p["id"] for p in profiles
                if stored_relation(p.get("relation")) == relation and p.get("kind") != "prospect"
                and p["id"] != _self_id(profiles)]
        if not hits:
            if word not in not_saved:
                not_saved.append(word)
        elif len(hits) == 1 or word in _PLURAL:
            for pid in hits:
                add(pid)
        elif not any(pid in chosen for pid in hits):
            # "my son" with two children saved as "child": which one is not
            # ours to guess, so neither is added and the answer says so.
            ambiguous[word] = [by_id[pid]["name"] for pid in hits]

    whole_family = bool(_FAMILY_RE.search(text))
    if whole_family:
        for p in profiles:
            if stored_relation(p.get("relation")) in FAMILY and p.get("kind") != "prospect":
                add(p["id"])

    # The reader takes part when they speak for themselves too ("we",
    # "Lakshmi and I"), or when nobody else was found. The person Ask is open
    # on goes first, since their chart anchors the answer.
    self_id = _self_id(profiles)
    if _SELF_RE.search(text):
        add(self_id or active_id)
    if not chosen:
        add(active_id)
    for anchor in (self_id, active_id):
        if anchor in chosen:
            chosen.remove(anchor)
            chosen.insert(0, anchor)
    chosen = chosen[:MAX_PEOPLE]
    return {"ids": chosen, "group": len(chosen) >= 2, "not_saved": not_saved,
            "ambiguous": ambiguous, "whole_family": whole_family}


def _self_id(profiles: list[dict]) -> str | None:
    return next((p["id"] for p in profiles if stored_relation(p.get("relation")) == "self"), None)
