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
from .intent import QuestionTense, detect_intent, detect_tense
from .registry import AGENT_REGISTRY, AgentConfig
from .safety import REFER_OUT_ANSWERS, refer_out_kind
from .schema import AskIntent, StructuredReading
from .validation_agent import ValidationAgent, ValidationProbeDraft, probe_violations
from .verifier import verify
from ..context import KeywordRouter, assemble_domain
from ..context.taxonomy import get_domain
from ..context.validation import validation_slots
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
    tense: QuestionTense
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
    tense: QuestionTense
    agent: DomainReadingAgent
    bundle: dict
    context_used: list[str]


@dataclass
class ValidationStore:
    """Everything the validation loop needs from persistence, as two plain
    callables — same pattern as `chart_loader`, and for the same reason:
    nothing in this module touches SQLAlchemy.

    `probes(domain)` returns the probes already recorded for this reader, this
    chart, and THAT DOMAIN (answered or not — an outstanding question must not
    be asked twice either). The domain argument is not a convenience: a probe
    answer is reader-typed free text about their own life, and an answer given
    to a wealth question has no business appearing in a marriage or health
    bundle. Scoping it here means that stays true as further domains ship,
    rather than becoming true only if whoever adds the next domain remembers.

    `commit(slot, draft) -> probe_id` writes the commitment and returns its id;
    it is called BEFORE the question is put to the reader, which is the whole
    contract of this feature. See db/models.py's ValidationProbe.
    """
    probes: Callable[[str], list[dict]]
    commit: Callable[[dict, ValidationProbeDraft], str]


@dataclass
class PrepareOutcome:
    """Either a terminal envelope (nothing left to generate) or a
    `PreparedRun` ready for `run()` — never both."""
    terminal_envelope: dict | None = None
    prepared: PreparedRun | None = None


# Ties (per the three-way design review): a single keyword hit is only
# "medium" confidence in KeywordRouter's scoring, not "low" — a lone,
# possibly-spurious match must not answer as confidently as a clean one.
# Clarify on zero-match ("low") always; on any real match, when a secondary
# domain scores within one hit of the primary — a genuine tie, not routine
# single-keyword ambiguity.
#
# 2026-08-09 (personality-domain independent review, two rounds): the
# original version only ran this tie check at confidence=="medium", never
# "high" (primary hits >= 2) — meaning a question that legitimately named
# two real keywords from the wrong domain (e.g. "temperament" + "character"
# for a spirituality question, both real, independently meaningful
# personality signals, not a double-count of the same phrase) could outscore
# a genuine one-keyword competitor and get answered with zero clarification
# signal, no matter how close the competitor's own count was. Both an
# independent review agent and this file's own precedent (KeywordRouter only
# checks presence, not exclusivity, per the settle-abroad incident) pointed
# at the same fix: the tie check is a property of the *margin* between
# primary and secondary, not of which confidence bucket the primary
# happened to land in — so it now runs whenever there is a real secondary
# domain to compare against, high confidence included.
def _needs_clarification(decision) -> bool:
    if decision.confidence == "low":
        return True
    if len(decision.ranked_domains) < 2:
        return False
    _primary_domain, primary_hits, _ = decision.ranked_domains[0]
    _secondary_domain, secondary_hits, _ = decision.ranked_domains[1]
    return (primary_hits - secondary_hits) <= 1


class AskOrchestrator:
    def __init__(self, chart_loader: Callable[[], VedicChart],
                router: KeywordRouter | None = None,
                validation_store: ValidationStore | None = None):
        """`chart_loader` is a zero-arg callable the route supplies —
        deferred so a bad-birth-data error only gets raised if a registered
        domain actually needs the chart (never for refer-out, never for
        clarification, never for a domain the registry doesn't have).

        `validation_store` is optional: without it the orchestrator behaves
        exactly as it did before this feature — no probes committed, and an
        empty `life_context` in the bundle."""
        self._chart_loader = chart_loader
        self._router = router or KeywordRouter()
        self._validation_store = validation_store

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
                tense=detect_tense(question),
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
            tense=detect_tense(question),
            needs_clarification=needs_clarification,
        )

    def check_registry(self, domain: str) -> RegistryResult:
        return RegistryResult(agent_config=AGENT_REGISTRY.get(domain))

    def assemble_context(self, domain: str, question: str) -> ContextResult:
        chart = self._chart_loader()
        bundle = assemble_domain(
            chart, domain, question=question,
            validation_probes=self._stored_probes(domain),
        )
        context_used = [
            key for key in _BUNDLE_TOP_LEVEL_SECTIONS
            if bundle.get(key)
        ]
        return ContextResult(bundle=bundle, context_used=context_used)

    def _stored_probes(self, domain: str) -> list[dict]:
        """This domain's probes only — see `ValidationStore`.

        Never let a probe-store failure cost the reader their reading. The loop
        is additive by construction: without it every reading is exactly the
        reading this app produced before the loop existed."""
        if self._validation_store is None:
            return []
        try:
            return self._validation_store.probes(domain)
        except Exception:
            return []

    def check_validation(self, prepared_bundle: dict, domain: str) -> dict | None:
        """Commit to a falsifiable claim, then return the question to ask —
        or None, which means "just answer them".

        The ordering here is the feature. `store.commit()` runs before this
        function returns, and the envelope it returns carries the question and
        options but deliberately NOT the committed claim: showing a reader what
        the chart expects before they answer tells them what to say, and the
        answer is then worth nothing. The claim is on the record in the
        database, which is where it needs to be for hit rate to mean anything.

        Everything here fails open. A slot picker that finds nothing, a model
        call that raises, a draft that fails `probe_violations`, a store that
        errors — all of them fall through to the ordinary reading path. A probe
        is a bonus; the answer is the product.
        """
        store = self._validation_store
        if store is None:
            return None
        try:
            asked = {probe.get("slot_id") for probe in self._stored_probes(domain)}
            slots = validation_slots(prepared_bundle, limit=1, exclude=asked)
            if not slots:
                return None
            slot = slots[0]
            draft = ValidationAgent(prepared_bundle, slot).run_probe()
            if probe_violations(draft, slot):
                return None
            probe_id = store.commit(slot, draft)
        except Exception:
            return None
        return {
            "type": "validation_needed",
            "domain": domain,
            "probe_id": probe_id,
            "slot_id": slot["slot_id"],
            "slot_kind": slot["kind"],
            "anchor": slot["anchor"],
            "question": draft.question,
            "options": [option.model_dump() for option in draft.options],
            "skippable": True,
        }

    def prepare(
        self, question: str, thread_domain: str | None = None,
        domain_override: str | None = None,
        experience_mode: str = "balanced",
        validate_first: bool = False,
    ) -> PrepareOutcome:
        """`experience_mode` (guided/balanced/practitioner) selects the
        agent's VOICE only — never its facts, claims, or guardrails. See
        `domain_agent.REGISTERS`. Defaults to balanced so a caller that
        doesn't supply one still gets the previous behaviour.

        `validate_first` opts this turn into the validation loop: the agent
        commits to a falsifiable claim about a dated window and asks the reader
        one multiple-choice question about it instead of answering immediately.
        Default False, so the loop is off until a client can render the
        `validation_needed` envelope — a question no UI displays is a wealth
        question that silently returns nothing. Answered probes flow back into
        the bundle as `life_context` regardless of this flag, so the readings
        improve as soon as any answers exist."""
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

        # After context assembly (the slot picker reads the bundle) and before
        # any reading is generated — a probe that arrived after the answer
        # would be asking about something already interpreted.
        if validate_first:
            probe_envelope = self.check_validation(context.bundle, routing.domain)
            if probe_envelope is not None:
                return PrepareOutcome(terminal_envelope=probe_envelope)

        agent = DomainReadingAgent(
            context.bundle, registry_result.agent_config.domain_addendum,
            question_tense=routing.tense,
            experience_mode=experience_mode,
        )
        return PrepareOutcome(prepared=PreparedRun(
            domain=routing.domain,
            intent=routing.intent,
            tense=routing.tense,
            agent=agent,
            bundle=context.bundle,
            context_used=context.context_used,
        ))

    def _agent_run_and_verify(self, prepared: PreparedRun, messages: list) -> AgentRunResult:
        try:
            reading = prepared.agent.run_structured_reading(messages)
        except Exception:
            return AgentRunResult(reading=None, violations=[], generation_failed=True)

        violations = verify(reading, prepared.bundle, prepared.domain, prepared.tense)
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

        violations = verify(reading, prepared.bundle, prepared.domain, prepared.tense)
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
                "domain": prepared.domain, "intent": prepared.intent,
                "tense": prepared.tense, "thread_id": thread_id,
            }
            return

        thread_id = persist(result.reading, "answered")
        yield {
            "type": "done", "status": "answered", "schema_version": SCHEMA_VERSION,
            "domain": prepared.domain, "intent": prepared.intent,
            "tense": prepared.tense,
            "context_used": prepared.context_used,
            "evidence_refs": [item.source for item in result.reading.technical_basis],
            "reading": result.reading.model_dump(),
            "thread_id": thread_id,
        }
