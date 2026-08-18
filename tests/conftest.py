"""Project-wide test safety nets.

Autouse fixtures here exist so a new code path reaching the real model
provider degrades to deterministic, in-process behavior by default, instead
of silently making a real network call. `test_validation_loop.py` already
carries its own narrower version of this idea (an autouse fixture that
fails any test reaching the provider layer through `run_probe`) after a
real incident — see docs/ask_context_engine_multi_agent_architecture_
2026-08-07.md's "Update 2026-08-11" for the story: a test that didn't stub
the model call passed for the wrong reason locally and failed for
reviewers with real credentials configured, and the fix was to make that
failure class un-writable rather than merely fix the one test.

This one exists for the same reason, one layer up. D2 (field-scoped
repair) gave `DomainReadingAgent` a second provider-reaching entry point,
`run_structured_repair`, alongside the original `run_structured_reading`.
Every test written before D2 that constructs a reading with ANY verifier/
coverage violation and mocks only `run_structured_reading` relied
—unknowingly— on repair reusing that same, already-mocked method; true
before D2, no longer true after, since a field-attributable violation now
routes through `run_structured_repair` instead.
"""
from unittest.mock import patch

import pytest

from astrospace.agents.domain_agent import DomainReadingAgent
from astrospace.agents.schema import StructuredReadingPatch


def _default_repair(self, messages, fields):
    """Reproduces the pre-D2 behavior every existing test that only mocks
    `run_structured_reading` was implicitly relying on: repair reuses
    whatever that mock currently returns, projected down to the fields
    D2 actually asked for. Calling `self.run_structured_reading(messages)`
    here invokes whatever the test's own `patch.object(...,
    "run_structured_reading", ...)` installed — `return_value`,
    `side_effect` list, or a real object — so a test whose mocked
    generation is already "good" gets a repair that's also good, and a
    test whose mock keeps returning the same "bad" reading gets a repair
    that reproduces the same failure, matching this file's own
    `_repair_with()`-style helpers used where a test wants the repair's
    outcome to differ from the original generation (see
    tests/test_profile_context_ledger_phase2.py and
    tests/test_ask_threads.py) — those tests override this default
    explicitly via their own `patch.object(DomainReadingAgent,
    "run_structured_repair", ...)`, which layers on top of this default
    for the scope of their own `with` block and reverts to it afterward,
    standard `unittest.mock` nesting.

    Installed with `new=` (a real function on the class), not
    `side_effect=` on a `MagicMock` — a `MagicMock` replacing a class
    attribute is not a descriptor, so `instance.method(...)` would call it
    WITHOUT `self`; a plain function assigned as a class attribute keeps
    normal method-binding behavior, which is what lets this call
    `self.run_structured_reading(...)`."""
    full = self.run_structured_reading(messages)
    return StructuredReadingPatch(**{f: getattr(full, f) for f in fields})


@pytest.fixture(autouse=True)
def _repair_defaults_to_the_mocked_generation():
    with patch.object(DomainReadingAgent, "run_structured_repair", new=_default_repair):
        yield
