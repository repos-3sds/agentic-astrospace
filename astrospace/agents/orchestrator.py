"""AskOrchestrator — the pipeline every Ask question runs through.

One class, but every internal step returns a typed result — graph
discipline (Safety -> Routing -> RegistryGate -> ContextAssembly ->
AgentRun -> Verify -> Persistence -> Response) without eleven node classes.

Split into two phases deliberately, matching what the route needs:
`prepare()` is synchronous and does everything that can fail with a normal
HTTP error (bad birth data) or short-circuit to a terminal answer (refer-out,
clarification, domain not ready) — the route calls this *before* creating
the StreamingResponse, so a bad-chart error still comes back as a proper
HTTPException instead of surfacing mid-stream where the status code can no
longer change. `run()` is the generator — only the actual model call,
verification, repair, and persistence happen lazily inside it.

No silent fallback: a domain the registry doesn't know about never reaches
a model call. `run()` never writes to the database before a verifier pass.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterator

from .domain_agent import DomainReadingAgent
from .intent import detect_intent
from .registry import AGENT_REGISTRY, AgentConfig
from .safety import REFER_OUT_ANSWERS, refer_out_kind
from .schema import AskIntent, StructuredReading
from .verifier import verify
from ..context import KeywordRouter, assemble_domain
from ..context.taxonomy import get_domain
from ..core.vedic.chart import VedicChart

SCHEMA_VERSION = "ask_structured_v1"

_BUNDLE_TOP_LEVEL_SECTIONS = (
    "houses", "karakas", "jaimini_karakas", "arudhas", "vargas",
    "yogas", "doshas", "dasha_relevance", "gochara", "references",
)


@dataclass
class SafetyResult:
    refer_out_kind: str | None


@dataclass
class RoutingResult:
    domain: str
    intent: AskIntent
    needs_clarification: bool
    available_domains: list[str] = field(default_factory=lambda: sorted(AGENT_REGISTRY))


@dataclass
class RegistryResult:
    agent_config: AgentConfig | None  # None => domain_not_ready


@dataclass
class ContextResult:
    bundle: dict
    context_used: list[str]


@dataclass
class AgentRunResult:
    reading: StructuredReading | None
    violations: list[str]
    generation_failed: bool = False


@dataclass
class PreparedRun:
    """Everything `run()` needs, resolved eagerly by `prepare()`."""
    domain: str
    intent: str
    agent: DomainReadingAgent
    bundle: dict
    context_used: list[str]


@dataclass
class PrepareOutcome:
    """Either a terminal envelope (nothing left to generate) or a
    `PreparedRun` ready for `run()` — never both."""
    terminal_envelope: dict | None = None
    prepared: PreparedRun | None = None


# Ties (per the three-way design review): a single keyword hit is only
# "medium" confidence in KeywordRouter's scoring, not "low" — a lone,
# possibly-spurious match must not answer as confidently as a clean one.
# Clarify on zero-match ("low") always; on a single-hit ("medium") only
# when a secondary domain scores within one hit of the primary — a genuine
# tie, not routine single-keyword ambiguity.
def _needs_clarification(decision) -> bool:
    if decision.confidence == "low":
        return True
    if decision.confidence != "medium" or len(decision.ranked_domains) < 2:
        return False
    _primary_domain, primary_hits, _ = decision.ranked_domains[0]
    _secondary_domain, secondary_hits, _ = decision.ranked_domains[1]
    return (primary_hits - secondary_hits) <= 1


class AskOrchestrator:
    def __init__(self, chart_loader: Callable[[], VedicChart],
                router: KeywordRouter | None = None):
        """`chart_loader` is a zero-arg callable the route supplies —
        deferred so a bad-birth-data error only gets raised if a registered
        domain actually needs the chart (never for refer-out, never for
        clarification, never for a domain the registry doesn't have)."""
        self._chart_loader = chart_loader
        self._router = router or KeywordRouter()

    def check_safety(self, question: str) -> SafetyResult:
        return SafetyResult(refer_out_kind=refer_out_kind(question))

    def route(
        self, question: str, thread_domain: str | None = None,
        domain_override: str | None = None,
    ) -> RoutingResult:
        """`thread_domain` is the domain the thread last actually answered
        in (the route resolves this from persisted history, if any) — a
        follow-up like "which month is strongest for this?" has zero
        domain keywords of its own and would otherwise trigger
        clarification on every turn after the first, breaking any
        pronoun-based follow-up. Only overrides when the *new* question
        has no independent signal (needs_clarification) — a follow-up that
        confidently names a different domain is a real topic switch and
        must not be silently pulled back to the old one.

        `domain_override` is a different thing entirely: an *explicit*
        reader choice (tapping a clarification chip), not an inferred one.
        It bypasses keyword scoring completely rather than being folded
        back into the question text — `KeywordRouter` only checks whether
        a keyword appears at least once, so re-mentioning "career" in a
        question that already said "career" once changes nothing, and the
        tie (e.g. against "marriage" also being present) never resolves.
        Prose-wrapping an explicit choice back through the same fuzzy
        router is how that turns into a stuck loop of identical
        clarifications with an ever-growing question string."""
        if domain_override:
            return RoutingResult(
                domain=domain_override,
                intent=detect_intent(question),
                needs_clarification=False,
            )
        decision = self._router.route(question)
        needs_clarification = _needs_clarification(decision)
        domain = decision.primary
        if needs_clarification and thread_domain and thread_domain in AGENT_REGISTRY:
            domain = thread_domain
            needs_clarification = False
        return RoutingResult(
            domain=domain,
            intent=detect_intent(question),
            needs_clarification=needs_clarification,
        )

    def check_registry(self, domain: str) -> RegistryResult:
        return RegistryResult(agent_config=AGENT_REGISTRY.get(domain))

    def assemble_context(self, domain: str, question: str) -> ContextResult:
        chart = self._chart_loader()
        bundle = assemble_domain(chart, domain, question=question)
        context_used = [
            key for key in _BUNDLE_TOP_LEVEL_SECTIONS
            if bundle.get(key)
        ]
        return ContextResult(bundle=bundle, context_used=context_used)

    def prepare(
        self, question: str, thread_domain: str | None = None,
        domain_override: str | None = None,
    ) -> PrepareOutcome:
        safety = self.check_safety(question)
        if safety.refer_out_kind:
            return PrepareOutcome(terminal_envelope={
                "type": "refer_out",
                "kind": safety.refer_out_kind,
                "answer": REFER_OUT_ANSWERS[safety.refer_out_kind],
            })

        routing = self.route(question, thread_domain=thread_domain, domain_override=domain_override)
        if routing.needs_clarification:
            return PrepareOutcome(terminal_envelope={
                "type": "clarification_needed",
                "options": routing.available_domains,
            })

        registry_result = self.check_registry(routing.domain)
        if registry_result.agent_config is None:
            return PrepareOutcome(terminal_envelope={
                "type": "domain_not_ready",
                "domain": routing.domain,
                "domain_label": get_domain(routing.domain).name,
                "available": routing.available_domains,
            })

        context = self.assemble_context(routing.domain, question)
        agent = DomainReadingAgent(context.bundle, registry_result.agent_config.domain_addendum)
        return PrepareOutcome(prepared=PreparedRun(
            domain=routing.domain,
            intent=routing.intent,
            agent=agent,
            bundle=context.bundle,
            context_used=context.context_used,
        ))

    def _agent_run_and_verify(self, prepared: PreparedRun, messages: list) -> AgentRunResult:
        try:
            reading = prepared.agent.run_structured_reading(messages)
        except Exception:
            return AgentRunResult(reading=None, violations=[], generation_failed=True)

        violations = verify(reading, prepared.bundle, prepared.domain)
        if not violations:
            return AgentRunResult(reading=reading, violations=[])

        # Exactly one repair attempt — hard cap, no open-ended retry loop.
        repair_messages = messages + [{
            "role": "user",
            "content": (
                "Your previous answer had these problems — answer again, fixing them, "
                "using only what is in the CONTEXT BUNDLE: " + "; ".join(violations)
            ),
        }]
        try:
            reading = prepared.agent.run_structured_reading(repair_messages)
        except Exception:
            return AgentRunResult(reading=None, violations=violations, generation_failed=True)

        violations = verify(reading, prepared.bundle, prepared.domain)
        if not violations:
            return AgentRunResult(reading=reading, violations=[])
        return AgentRunResult(reading=None, violations=violations)

    def run(
        self, prepared: PreparedRun, messages: list,
        persist: Callable[[StructuredReading | None, str], str | None],
    ) -> Iterator[dict]:
        """`persist(reading, status) -> thread_id | None` is supplied by the
        route (a closure over its DB session/thread/user) — nothing here
        touches SQLAlchemy. Called exactly once, and only after a verifier
        pass (or a terminal failure state) — never before."""
        yield {"type": "status", "stage": "gathering_context",
              "label": f"Gathering your {', '.join(prepared.context_used[:3])}…"}
        yield {"type": "status", "stage": "interpreting",
              "label": f"{prepared.bundle.get('domain_name', prepared.domain)} specialist is interpreting…"}

        result = self._agent_run_and_verify(prepared, messages)

        if result.reading is None:
            status = "generation_failed" if result.generation_failed else "verification_failed"
            thread_id = persist(None, status)
            yield {
                "type": "done", "status": status, "schema_version": SCHEMA_VERSION,
                "domain": prepared.domain, "intent": prepared.intent, "thread_id": thread_id,
            }
            return

        thread_id = persist(result.reading, "answered")
        yield {
            "type": "done", "status": "answered", "schema_version": SCHEMA_VERSION,
            "domain": prepared.domain, "intent": prepared.intent,
            "context_used": prepared.context_used,
            "evidence_refs": [item.source for item in result.reading.technical_basis],
            "reading": result.reading.model_dump(),
            "thread_id": thread_id,
        }
