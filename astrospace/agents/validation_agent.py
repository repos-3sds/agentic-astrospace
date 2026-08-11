"""The commit-before-ask turn: the agent states what it expects, then asks.

The engine has already decided WHERE this chart is ambiguous
(`context/validation.py`). This module covers the other half — writing the
question and, first, committing to an answer.

Order is the whole design. A validation loop that asks before it commits is a
cold-reading machine wearing a chart: the reader discloses, the agent reflects
the disclosure back as insight, and nothing has been tested. Committing first
buys three things at once:

  * honesty — the chart is on the record before the reader speaks, so a
    confirmation is evidence rather than an echo;
  * measurement — hit rate becomes a real number, which this product currently
    does not have for any reading it produces;
  * learning — a persistent miss is signal, and for a house-sensitive slot it
    is specifically a birth-time signal.

The model produces the claim and the question in one call, which is fine: no
answer exists yet either way. What makes the commitment binding is that it is
persisted before the question is emitted, and that nothing downstream can
revise it (see `db/crud_mobile.record_validation_answer`).

The reader is never shown the committed claim before answering. That is not a
UI detail — showing it would tell them what the chart "wants" to hear and
contaminate the only evidence this loop collects.
"""
from __future__ import annotations

import json

from pydantic import BaseModel, Field

from .base import BaseAstroAgent

# Candidate keys the agent may NOT commit to. "skip" is the reader's decline
# and "neither" is a null result — both are legitimate ANSWERS, and neither is
# a claim about the chart. A probe whose prediction is "neither of my own
# readings" tests nothing.
NON_COMMITTABLE = {"skip", "neither"}


class ValidationOption(BaseModel):
    key: str = Field(description="Exactly one of the candidate keys supplied in the slot — never a new one.")
    label: str = Field(description="The option as the reader sees it: plain, short, concrete, no jargon.")


class ValidationProbeDraft(BaseModel):
    """What the model returns. Field order mirrors the required thinking
    order — commit, then ask — even though both arrive in one call."""

    committed_claim: str = Field(
        description="What you expect the reader to say, stated as a falsifiable sentence "
                    "about this dated window. Specific enough to be wrong."
    )
    committed_candidate: str = Field(
        description="The candidate key your claim commits to. Must be one of the slot's "
                    "substantive candidates — never 'neither' and never 'skip'."
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="How strongly the chart supports that candidate over the others, 0-1. "
                    "Track the chart, not the format: if the placements barely favour one "
                    "reading, say 0.4 and mean it.",
    )
    question: str = Field(
        description="One short, direct question to the reader about the anchored window. "
                    "Plain Indian English, under 25 words, no preamble."
    )
    options: list[ValidationOption] = Field(
        description="One option per candidate key in the slot, including 'neither' and 'skip'."
    )


_SYSTEM = """You are AstroSpace's validation specialist for the {domain_name} domain. You are
not writing a reading. You are running one honest test of whether this chart matches the life
the reader has actually lived.

The engine has already found where this chart is genuinely ambiguous and handed you the slot
below. You do not choose the topic, and you must not ask about anything outside it.

AMBIGUITY SLOT:
{slot_json}

CHART CONTEXT (the same verified bundle the reading specialists use):
{bundle_json}

Do this, in this order:

1. COMMIT FIRST. Before you write the question, decide which candidate this chart actually
   supports most, and say so in `committed_claim` as a sentence that could turn out to be
   wrong. "Between {anchor_start} and {anchor_end} their money mostly came through X, not Y"
   is a commitment. "There may have been financial changes" is not — it cannot be wrong, so
   it tests nothing. Anchor the claim to the slot's dates, and never past {anchor_end}: that
   is either when the period ended or today, and the reader can only speak to years they have
   actually lived. If the slot's anchor says `in_progress`, the window is still running — say
   "since {anchor_start}" or "so far", never imply it is finished.
2. SET A HONEST CONFIDENCE. It must track how much the chart actually separates the
   candidates. Two evenly-matched readings are a 0.4, not a 0.55 dressed up.
3. THEN WRITE THE QUESTION. One sentence, direct, about the anchored window, in the reader's
   own categories — savings, income, loans and EMIs, land and property, gold, family
   responsibilities, job versus own business. Ask what happened, never what the chart says.
   The reader is Indian, most often South Indian; Rahu, Shani, Guru and dasha are household
   words, so do not translate them and do not lecture. Naming the period plainly ("since your
   Venus dasha started in 2021, when you were 27") is good; explaining what a dasha is, is not.
4. WRITE THE OPTIONS. One per candidate key in the slot, in the reader's language, concrete
   enough to pick between at a glance. Keep the keys exactly as given. Include the 'neither'
   and 'skip' options — a question the reader cannot answer "no" to is not a test.

Hard rules:
- Never reveal, hint at, or lean the question toward your committed claim. A question that
  telegraphs the expected answer destroys the only evidence this turn collects.
- Never state a life event as fact. You know when their periods turned. You do not know what
  happened to them — that is the entire reason you are asking.
- Never ask about death, illness, or a legal or financial verdict, about the reader or about
  anyone in their family, in any phrasing.
- No preamble, no reassurance, no reading. One claim, one question, the options."""


class ValidationAgent(BaseAstroAgent):
    """Writes one probe for one engine-selected slot."""

    def __init__(self, bundle: dict, slot: dict, api_key: str = None):
        super().__init__(api_key)
        self.bundle = bundle
        self.slot = slot
        anchor = slot.get("anchor") or {}
        self.system_prompt = _SYSTEM.format(
            domain_name=bundle.get("domain_name", bundle.get("domain", "")),
            slot_json=json.dumps(slot, indent=2, default=str),
            bundle_json=json.dumps(bundle, indent=2, default=str),
            anchor_start=anchor.get("start", "the window start"),
            anchor_end=anchor.get("end", "the window end"),
        )

    def run_probe(self) -> ValidationProbeDraft:
        return self.run_structured(
            [{"role": "user", "content":
              "Commit to what you expect, then ask the reader one question about that window."}],
            ValidationProbeDraft, tool_name="deliver_validation_probe",
        )


def probe_violations(draft: ValidationProbeDraft, slot: dict) -> list[str]:
    """Deterministic checks on a draft, in the same spirit as `verifier.py`:
    shape is Pydantic's job, this judges content.

    A probe that fails these is dropped and the reader simply gets their
    reading — a broken probe must never cost someone their answer, so nothing
    here retries or repairs.
    """
    violations: list[str] = []
    keys = {c["key"] for c in slot.get("candidates") or []}
    committable = keys - NON_COMMITTABLE

    if draft.committed_candidate not in committable:
        violations.append(
            f"committed_candidate {draft.committed_candidate!r} is not one of this "
            f"slot's substantive candidates {sorted(committable)}"
        )
    offered = {option.key for option in draft.options}
    if unknown := offered - keys:
        violations.append(f"options introduce candidate keys the slot never offered: {sorted(unknown)}")
    if missing := committable - offered:
        violations.append(f"options omit substantive candidates the reader must be able to pick: {sorted(missing)}")
    if "skip" in keys and "skip" not in offered:
        violations.append("options omit the skip option — every probe must be declinable")
    if not draft.committed_claim.strip():
        violations.append("committed_claim is empty — there is nothing to test")
    # A claim the reader can read off the question is not a blind test. Cheap
    # substring check only; the prompt carries the real instruction.
    if draft.committed_claim.strip().lower() in draft.question.strip().lower():
        violations.append("question repeats the committed claim verbatim — it telegraphs the expected answer")
    return violations
