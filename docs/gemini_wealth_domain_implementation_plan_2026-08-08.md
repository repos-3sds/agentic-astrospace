# Wealth Domain Spec Implementation Plan

**Date:** 2026-08-08
**Author:** Gemini

This plan outlines the steps for Part 2 of the task brief: implementing the Wealth domain spec in the AstroSpace agentic backend. 

## 1. Goal

Integrate the Wealth domain into the agent registry and add corresponding test coverage, acting as a production trust boundary to ensure the model responds properly and safely to wealth-related queries.

## 2. Review Requirements

A new entry in `AGENT_REGISTRY` turns on live model answers for real users. Per the rules in `AGENTS.md`, this is **not** append-only-safe and must go through a PR for owner review (Claude). Do not merge directly to `main` until this review is complete.

## 3. Proposed Changes

### `astrospace/agents/registry.py`

1.  **Add `_WEALTH_ADDENDUM`**:
    Define a string `_WEALTH_ADDENDUM` that follows the same framing as `_CAREER_ADDENDUM` and `_MARRIAGE_ADDENDUM`.
    *   The addendum will explicitly reinforce the boundary set by `safety.py`'s `refer_out_kind()`, which blocks directive-seeking money questions ("should I buy/sell/invest").
    *   It will frame the agent's role around timing and suitability (e.g., "is this a good year for my finances") rather than investment-directive language.
2.  **Update `AGENT_REGISTRY`**:
    Add the `wealth` domain configuration to the `AGENT_REGISTRY` mapping:
    ```python
    "wealth": AgentConfig(domain_id="wealth", domain_addendum=_WEALTH_ADDENDUM)
    ```

### `tests/test_domain_agent.py`

Add tests following the existing patterns for the Career and Marriage domains:
1.  **Bundle Shape Test**: Add a test verifying the response bundle shape for the wealth domain.
2.  **Routing Test**: Add an `AskOrchestrator.prepare()` test that verifies routing for a wealth-related question (e.g., "When will my financial situation improve?").
3.  **Tie-Breaker Test**: Ensure wealth keywords do not inappropriately overlap or cause ambiguous ties with career/marriage in ways that break existing tests.

## 4. Verification Plan

Run the test suite to ensure the new domain configuration works seamlessly with the orchestrator:
- `pytest tests/test_domain_agent.py`
- `pytest tests/test_verifier.py`

## 5. Execution Strategy (Branching)

To respect Rule 3b and avoid disrupting the shared working directory:
1. I will create a `git worktree` in my private agent scratch directory.
2. I will implement these changes in the worktree on a new branch (`gemini/wealth-domain-spec`).
3. I will push the branch and open a PR tagged for Claude's review.
