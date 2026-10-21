"""One owner for Ask's terminal texts (audit I8): both routes call
orchestrator.terminal_turn, so the JSON route and the stream cannot drift."""
import pytest

from astrospace.agents.orchestrator import terminal_turn


def test_every_terminal_state_has_text_and_evidence():
    envelopes = [
        {"type": "refer_out", "answer": "Please see a doctor.", "kind": "medical"},
        {"type": "validation_needed", "question": "Did you move house?", "domain": "career",
         "probe_id": "p1", "slot_id": "s1", "options": ["Yes", "No"]},
        {"type": "clarification_needed", "options": ["career", "marriage"]},
        {"type": "context_unavailable", "domain": "career"},
        {"type": "domain_not_ready", "domain": "travel", "domain_label": "Travel",
         "available": ["Career", "Marriage"]},
    ]
    for envelope in envelopes:
        turn = terminal_turn(envelope)
        assert turn.content.strip()
        assert turn.evidence


def test_refer_out_keeps_its_kind_and_the_claim_never_reaches_history():
    assert terminal_turn({"type": "refer_out", "answer": "x", "kind": "legal"}).refer_out_kind == "legal"
    turn = terminal_turn({"type": "validation_needed", "question": "Q?", "domain": "career",
                          "probe_id": "p", "slot_id": "s", "options": [], "claim": "secret"})
    assert "secret" not in turn.content and "claim" not in turn.evidence


def test_an_unknown_state_is_refused():
    with pytest.raises(ValueError):
        terminal_turn({"type": "something_new"})
