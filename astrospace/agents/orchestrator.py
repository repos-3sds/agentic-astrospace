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

import json
import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Iterator

from .ask_tools import ChartTools, summarize_call
from .domain_agent import DomainReadingAgent
from .explorer import ChartExplorer
from .intent import QuestionTense, detect_intent, detect_tense
from .registry import AGENT_REGISTRY, AgentConfig
from .safety import REFER_OUT_ANSWERS, refer_out_kind
from .scope import QuestionPlan, fixed_reply, plan_question
from .schema import AskIntent, StructuredReading
from .stance import detect_pushback
from .validation_agent import ValidationAgent, ValidationProbeDraft, probe_violations
from .verifier import (guided_violations, quality_violations, safety_violations, verify,
                       verify_coverage, violation_fields)
from ..context.muhurta_search import muhurta_section
from ..context import KeywordRouter, assemble_domain
from ..context.focus import focus_bundle
from ..context.profile_context import LogicalPreflight, build_logical_preflight
from ..context.taxonomy import get_domain
from ..context.validation import validation_slots
from ..core.vedic.chart import VedicChart
from ..core.vedic.favourable import shade_verdicts
from ..core.vedic.positions import sign_index

SCHEMA_VERSION = "ask_structured_v1"

_BUNDLE_TOP_LEVEL_SECTIONS = (
    "houses", "karakas", "jaimini_karakas", "arudhas", "vargas",
    "yogas", "doshas", "dasha_relevance", "gochara", "references",
    "muhurta_search",
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
    # True only when a CONFIGURED profile_context_store raised on this turn
    # — never when no store was supplied at all (that stays additive/off,
    # see `AskOrchestrator.__init__`'s docstring). `prepare()` turns this
    # into a terminal `context_unavailable` envelope rather than silently
    # generating against an empty, unconstrained projection — see
    # `check_profile_context()`.
    profile_context_unavailable: bool = False


# One line per Ask turn, JSON, so the cost per verified answer can be read
# off the logs for the two weeks the launch plan asks for before quotas are
# fixed. Nothing in it identifies the reader beyond the thread id.
cost_log = logging.getLogger("astrospace.ask.cost")
log = logging.getLogger(__name__)

# The tool-using Ask's exploring step gives up after this long and the turn
# carries on over the plain bundle.
EXPLORE_TIMEOUT_S = 90

EXPLORED_NOTE = """

LOOKED UP FOR THIS QUESTION: the bundle's `explored` list holds chart lookups made for this
exact question, each with a `ref` (e.g. "tool:house(7)"). `explorer_notes` sums them up,
`rule_verdicts` says for each classical rule whether it holds, partly holds, fails or REVERSES
for this chart, and `reader_facts` is what the reader has told Siddha about their life.
- Use the lookups like any other bundle section; weigh dignity, the three lagnas, the varga,
  nakshatras and the sub-sub period timing they show.
- A rule marked fails or reverses must not be used for the claim it was written for; a reversed
  rule points the other way (e.g. Jupiter in the 10th from the Moon is a strain). Only rules
  marked holds or partly may be cited as a `technical_basis` source.
- Start from `reader_facts`: never assume a life the reader has said they do not have.
- Each rule verdict carries an `effect` (helps, hurts, mixed) for this question; a rule that
  holds and hurts is a caution, never support.
- The explorer judged every angle ("Angle ..." lines) and the code weighed them into one
  "Overall" line. Your verdict follows that Overall band (good, moderately good, mixed, weak,
  avoid for now); never let one angle or one number decide. Walk the reader through the main
  angles in plain words, the strongest for and against, then the combined view. Set
  confidence to medium when the band is mixed or moderately good.
- Copy dates from the looked-up periods and the explorer's Timing line exactly.
- Tie the person's nature to the running periods ("Personality in this period"), and carry the
  explorer's Take care / Consider / Avoid / Do lines into `guidance.practical_actions`, each
  starting with that word, when the question asks what to do or what lies ahead.
- `guidance.remedies`: 1-2 only, taken from the "Remedy ..." lines (the reader's remedy plan),
  with the mantra in English letters and why it fits them. Never invent a remedy.
- Tier H patterns and nakshatra deity stories are practice, not classics: say so in plain words
  if you lean on one. Never name a book in the reader-facing text."""


READER_SAID_NOTE = """

WHAT THE READER SAID BEFORE: `reader_said_before` holds the reader's own earlier questions on
this profile, newest first. Read them before answering: they often state life facts (never
worked, tried a business, health worries, what they already rejected). Build the answer on
those facts, name the ones that matter in plain words, and never suggest something they said
they cannot do or already tried without saying how this time differs.
- Keep the voice of THIS question: if it asks about "she", "he" or "my daughter", write about
  that person in the third person, even when the earlier messages were written as "I".
- Do not add dates or details to what they told you; if the chart suggests when something
  happened, say it as the chart's view ("the chart points to around ...") and ask.
- Stay measured: "suits you best", never "your true path", "destiny" or "for sure"."""


def reader_said_before(history: list[str] | None, question: str) -> list[str]:
    """The reader's earlier questions on this profile, cleaned for the
    prompt: the owner's "/old " prefix dropped, repeats and the current
    question left out, newest first, at most 12."""
    seen = {" ".join(question.lower().split())}
    out: list[str] = []
    for line in history or []:
        text = str(line or "").strip()
        if text.lower().startswith("/old "):
            text = text[5:].strip()
        key = " ".join(text.lower().split())
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(text[:500])
    return out[:12]


def _usage_summary(usage: dict) -> dict:
    """The persisted/streamed shape: totals without the per-call breakdown."""
    return {
        "provider": usage.get("provider"), "model": usage.get("model"),
        "calls": int(usage.get("calls") or 0),
        "input_tokens": int(usage.get("input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
        "repaired": bool(usage.get("repaired")),
        "latency_ms": usage.get("latency_ms"),
    }


@dataclass
class AgentRunResult:
    reading: StructuredReading | None
    violations: list[str]
    generation_failed: bool = False
    # Token usage of every model call this turn made — the first generation
    # and the repair pass alike — as `BaseAstroAgent.usage_totals()` reports
    # it. Filled by `_agent_run_and_verify()` on every path, failures too.
    usage: dict = field(default_factory=dict)
    # Quality violations that survived the repair attempt. The reading still
    # ships; this records what it fell short on so the gap is visible in logs
    # and measurable, rather than silently absorbed.
    quality_shortfall: list[str] = field(default_factory=list)


@dataclass
class PreparedRun:
    """Everything `run()` needs, resolved eagerly by `prepare()`."""
    domain: str
    intent: str
    tense: QuestionTense
    agent: DomainReadingAgent
    bundle: dict
    context_used: list[str]
    # The exact profile-context snapshot this turn's agent was prompted
    # with — carried alongside the bundle (not re-derived from it) so
    # `run()` can report the revision/as_of this answer is grounded in
    # without re-reading `bundle["profile_context"]`'s shape.
    profile_context_revision: int = 0
    profile_context_as_of: str | None = None
    # What kind of question this is (agents/scope.py): sets the answer's
    # length and what the prose may bring in.
    question_kind: str = "broad"
    # Set by `run()` before it calls `persist`, so the route's persist
    # closure can store the cost of the answer it is writing without the
    # callback signature changing: {"provider", "model", "calls",
    # "input_tokens", "output_tokens", "repaired", "latency_ms", "breakdown"}.
    usage: dict = field(default_factory=dict)
    # Set only when this turn uses the tool-using Ask (agents/ask_engine.py).
    # `explorer_factory(on_tool)` builds the exploring agent; after it runs,
    # `agent_factory(bundle)` rebuilds the specialist over the bundle with
    # the explored results in it.
    explorer_factory: Callable | None = None
    agent_factory: Callable | None = None
    explore_usage: list = field(default_factory=list)
    # guided / balanced / practitioner: Guided answers are also checked for
    # chart terms in the prose (verifier.guided_violations).
    experience_mode: str = "balanced"
    # The explorer's angle-by-angle weighing for the reader (explorer.weighing_view).
    weighing: dict | None = None


@dataclass
class ProfileContextStore:
    """DB-touching callable the route supplies — same pattern as
    `ValidationStore`/`chart_loader`, and for the same reason: nothing in
    this module touches SQLAlchemy.

    `projection(domain, as_of_iso) -> dict` must return the plain-dict form
    of a `FrozenProfileContextProjection`
    (`astrospace/db/crud_profile_context.py`'s `build_profile_context_projection()`
    `.to_dict()`) — already domain-filtered and current-as-of, built exactly
    once per call. The orchestrator calls this exactly once per turn, before
    `AgentRun`, and never again during repair or verification — see
    `check_profile_context()`."""
    projection: Callable[[str, str], dict]


@dataclass
class ProfileContextResult:
    bundle_section: dict  # the projection dict, plus a "preflight" key
    preflight: LogicalPreflight
    # See `ContextResult.profile_context_unavailable` — same distinction,
    # one level lower.
    unavailable: bool = False


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


@dataclass(frozen=True)
class TerminalTurn:
    """What a terminal envelope says to the reader, and how the turn is stored."""
    content: str
    domain: str | None
    refer_out_kind: str | None
    evidence: dict


def domain_labels(domain_ids: list[str]) -> list[str]:
    """Readable names for the clarify reply ("Family & property"), never the
    internal ids ("family_property") readers were shown before."""
    labels = []
    for domain_id in domain_ids:
        try:
            labels.append(get_domain(domain_id).name.lower())
        except Exception:
            labels.append(domain_id.replace("_", " "))
    return labels


def _recent_reader_text(question: str, history: list[dict] | None) -> str:
    """The question plus the reader's last few turns: a shade list given two
    turns ago is still what "which of these?" is about."""
    earlier = [str(turn.get("content") or "") for turn in (history or [])[-6:]
               if turn.get("role") == "user"]
    return "\n".join([*earlier, question])


def terminal_turn(envelope: dict) -> TerminalTurn:
    """The reader-facing text for every terminal state `prepare()` can end in.

    Both Ask routes (the JSON one and the stream) used to write these texts
    each on their own, and had drifted: only the stream knew
    validation_needed (audit I8). Raises ValueError on a state this does not
    know, so a new one cannot reach a reader as an empty answer.
    """
    kind = envelope["type"]
    if kind == "refer_out":
        return TerminalTurn(envelope["answer"], None, envelope["kind"],
                            {"safety_policy": "excluded_verdict"})
    if kind == "validation_needed":
        # The stored turn carries the question and the options, never the
        # committed claim: thread history is replayed to the model on later
        # turns, and a claim visible there would let a future reading launder
        # its own prediction as evidence. The commitment lives in
        # validation_probes, which nothing replays.
        return TerminalTurn(envelope["question"], envelope["domain"], None,
                            {"status": "validation_needed", "probe_id": envelope["probe_id"],
                             "slot_id": envelope["slot_id"], "options": envelope["options"]})
    if kind == "clarification_needed":
        return TerminalTurn(
            f"I can help with: {', '.join(domain_labels(envelope['options']))} right now — "
            "which one is this about?",
            None, None, {"clarification_options": envelope["options"]})
    if kind == "context_unavailable":
        # A configured ProfileContextStore raised for this turn (see
        # check_profile_context()): the reader's saved facts could not be
        # checked, so this must not fall through to a reading that would look
        # just as confident either way. No fact values are surfaced.
        return TerminalTurn(
            "I couldn't check your saved profile context just now, so I'm holding off "
            "on this answer rather than risk missing something you've already told me. "
            "Please try again in a moment.",
            envelope["domain"], None, {"status": "context_unavailable", "retryable": True})
    if kind == "domain_not_ready":
        return TerminalTurn(
            f"{envelope['domain_label']} isn't ready yet. "
            f"I can currently help with: {', '.join(envelope['available'])}.",
            envelope["domain"], None, {"status": "domain_not_ready", "available": envelope["available"]})
    raise ValueError(f"Unhandled orchestrator terminal state: {kind!r}")


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


def exploration_trace(prepared: "PreparedRun") -> dict | None:
    """What the tool-using Ask looked up this turn, small enough to store
    with the answer: each call's tool, arguments and ref, the pattern ids it
    was shown, and the explorer's notes. None when the turn did not explore."""
    calls = prepared.bundle.get("explored") or []
    if not calls:
        return None
    return {
        "calls": [{"tool": c.get("tool"), "args": c.get("args") or {}, "ref": c.get("ref"),
                   "failed": "error" in (c.get("result") or {}),
                   **({"patterns": [row.get("id") for row in (c.get("result") or {}).get("patterns") or []]}
                      if (c.get("result") or {}).get("patterns") else {})}
                  for c in calls],
        "notes": prepared.bundle.get("explorer_notes") or "",
        "rule_verdicts": prepared.bundle.get("rule_verdicts") or {},
        "reader_facts": prepared.bundle.get("reader_facts") or [],
        "overall_view": prepared.bundle.get("overall_view"),
        "weighing": prepared.weighing,
    }


class AskOrchestrator:
    def __init__(self, chart_loader: Callable[[], VedicChart],
                router: KeywordRouter | None = None,
                validation_store: ValidationStore | None = None,
                profile_context_store: ProfileContextStore | None = None,
                planner: Callable[[str, list[dict] | None], QuestionPlan] | None = None):
        """`chart_loader` is a zero-arg callable the route supplies —
        deferred so a bad-birth-data error only gets raised if a registered
        domain actually needs the chart (never for refer-out, never for
        clarification, never for a domain the registry doesn't have).

        `validation_store` is optional: without it the orchestrator behaves
        exactly as it did before this feature — no probes committed, and an
        empty `life_context` in the bundle.

        `profile_context_store` is optional in exactly the same sense, and
        for the same reason: without it every reading behaves exactly as it
        did before Phase 2 — an empty `profile_context` bundle section, no
        logical preflight constraints, nothing new for the verifier to
        check. A store failure fails open the same way a validation-store
        failure does (see `check_profile_context()`) — reader-authored
        context is additive, never a hard dependency for answering."""
        self._chart_loader = chart_loader
        self._router = router or KeywordRouter()
        # Sorts the question before anything is loaded (agents/scope.py).
        self._planner = planner or plan_question
        self._validation_store = validation_store
        self._profile_context_store = profile_context_store
        self._chart: VedicChart | None = None

    def check_safety(self, question: str) -> SafetyResult:
        return SafetyResult(refer_out_kind=refer_out_kind(question))

    def route(
        self, question: str, thread_domain: str | None = None,
        domain_override: str | None = None,
        sorted_domain: str | None = None,
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
        # The sorter read the question's meaning, so it wins over a lone
        # keyword hit: "AI characters for her YouTube channel, can she earn?"
        # matched personality on "character" alone. Two or more hits for one
        # area ("promotion at work") still win. The sorter also comes before
        # the thread's old domain, because it saw the thread and can tell a
        # topic switch from a follow-up.
        if (sorted_domain and sorted_domain in AGENT_REGISTRY
                and (needs_clarification or decision.confidence != "high")):
            domain = sorted_domain
            needs_clarification = False
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

    def assemble_context(self, domain: str, question: str,
                         tense: QuestionTense = "unspecified",
                         intent: AskIntent | None = None,
                         question_kind: str = "broad",
                         history: list[dict] | None = None) -> ContextResult:
        chart = self._chart_loader()
        self._chart = chart
        bundle = assemble_domain(
            chart, domain, question=question, intent=intent,
            validation_probes=self._stored_probes(domain),
        )
        bundle = focus_bundle(bundle, question_kind, question)
        # Shades the reader named this turn or in their recent turns, each
        # sorted in code, so "But I like Magma Red" meets the same verdict
        # the list of colours got two turns earlier.
        shades = shade_verdicts(_recent_reader_text(question, history),
                                sign_index(chart.lagna_lon))
        if shades:
            bundle["functional_planets"] = {**bundle["functional_planets"],
                                            "shades_asked": shades}
        # "When is a good time to..." gets the Muhurta screen's real slots.
        search = muhurta_section(chart, question)
        if search:
            bundle["muhurta_search"] = search
        profile_context = self.check_profile_context(bundle, domain, question, tense)
        bundle["profile_context"] = profile_context.bundle_section
        context_used = [
            key for key in _BUNDLE_TOP_LEVEL_SECTIONS
            if bundle.get(key)
        ]
        return ContextResult(bundle=bundle, context_used=context_used,
                             profile_context_unavailable=profile_context.unavailable)

    def check_profile_context(self, bundle: dict, domain: str, question: str,
                              tense: QuestionTense) -> ProfileContextResult:
        """Builds the frozen projection EXACTLY ONCE per call — the store's
        `projection()` callable is invoked here and nowhere else in this
        module. `assemble_context()` calls this once, before `AgentRun`;
        neither the one repair attempt nor `verify()`/`verify_coverage()`
        ever calls back into the store, so the same snapshot governs
        generation, repair, and verification for this turn — the "freeze
        context per Ask turn" requirement.

        No store at all (`self._profile_context_store is None`) is additive
        and fails open, same discipline as `_stored_probes()` — every caller
        that never configured a ledger continues to behave exactly as before
        Phase 2. A CONFIGURED store that raises is a different situation
        entirely: silently substituting an empty "ready" projection here is
        exactly the retired/married/health trust hole Phase 2 exists to
        close (a saved fact the reader already gave us going unenforced
        because of a transient query failure, with the answer looking
        identically confident either way). That case is flagged via
        `unavailable=True` instead — `AskOrchestrator.prepare()` turns it
        into a terminal `context_unavailable` envelope and generation never
        runs."""
        empty = {
            "facts": [], "logical_constraints": [], "revision": 0,
            "as_of": (bundle.get("profile_facts") or {}).get("as_of", ""),
            "domain": domain, "status": "ready", "contradictions": [],
        }
        unavailable = False
        if self._profile_context_store is None:
            projection = empty
        else:
            try:
                as_of_date = str((bundle.get("profile_facts") or {}).get("as_of") or "")[:10]
                projection = self._profile_context_store.projection(domain, as_of_date)
            except Exception:
                log.exception("profile context projection failed (domain=%s)", domain)
                projection = empty
                unavailable = True

        preflight = build_logical_preflight(
            profile_facts=bundle.get("profile_facts") or {},
            projection_facts=projection.get("facts") or [],
            tense=tense, question=question, domain=domain,
            contradictions=tuple(projection.get("contradictions") or ()),
        )
        return ProfileContextResult(
            bundle_section={**projection, "preflight": preflight.to_dict()},
            preflight=preflight,
            unavailable=unavailable,
        )

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
            log.exception("validation probe lookup failed (domain=%s)", domain)
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
            log.exception("validation probe failed; answering directly (domain=%s)", domain)
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
        language: str = "en",
        validate_first: bool = False,
        tone: str = "gentle",
        history: list[dict] | None = None,
        explore: bool = False,
        explore_history: list[str] | None = None,
    ) -> PrepareOutcome:
        """`experience_mode` (guided/balanced/practitioner) selects the
        agent's VOICE only — never its facts, claims, or guardrails. See
        `domain_agent.REGISTERS`. Defaults to balanced so a caller that
        doesn't supply one still gets the previous behaviour. `tone`
        (gentle/direct, `domain_agent.TONES`) is the same kind of
        delivery-only switch.

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

        # Outside the app's theme, or a greeting: a fixed reply, no chart, no
        # model, no Ask credit (terminal envelopes never reserve one). A
        # reader who tapped a domain chip has already said what it is about.
        plan = (QuestionPlan(kind="narrow", method="override") if domain_override
                else self._planner(question, history))
        if plan.kind in ("off_topic", "greeting"):
            log.info("ask question declined as %s (%s)", plan.kind, plan.method)
            return PrepareOutcome(terminal_envelope={
                "type": "refer_out",
                "kind": "out_of_scope" if plan.kind == "off_topic" else "greeting",
                "answer": fixed_reply(plan.kind, language),
            })

        routing = self.route(question, thread_domain=thread_domain,
                             domain_override=domain_override, sorted_domain=plan.domain)
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

        context = self.assemble_context(routing.domain, question, routing.tense,
                                        routing.intent, question_kind=plan.kind,
                                        history=history)
        if context.profile_context_unavailable:
            # A configured ledger failed to answer for this turn — must not
            # fall through to a normal reading, which would look identically
            # confident whether or not the reader's saved facts were actually
            # enforced. No fact values are exposed here, only that the check
            # could not be made; the reader is asked to retry rather than
            # given a possibly-unconstrained answer.
            return PrepareOutcome(terminal_envelope={
                "type": "context_unavailable",
                "domain": routing.domain,
                "retryable": True,
            })

        # After context assembly (the slot picker reads the bundle) and before
        # any reading is generated — a probe that arrived after the answer
        # would be asking about something already interpreted.
        if validate_first:
            probe_envelope = self.check_validation(context.bundle, routing.domain)
            if probe_envelope is not None:
                return PrepareOutcome(terminal_envelope=probe_envelope)

        said = reader_said_before(explore_history, question) if explore else []
        if said:
            context.bundle["reader_said_before"] = said

        def build_agent(bundle: dict) -> DomainReadingAgent:
            agent = DomainReadingAgent(
                bundle, registry_result.agent_config.domain_addendum,
                question_tense=routing.tense,
                question_kind=plan.kind,
                experience_mode=experience_mode,
                language=language,
                tone=tone,
                pushback=detect_pushback(question),
            )
            if bundle.get("explored"):
                agent.system_prompt += EXPLORED_NOTE
            if bundle.get("reader_said_before"):
                agent.system_prompt += READER_SAID_NOTE
            return agent

        agent = build_agent(context.bundle)
        explorer_factory = None
        if explore and self._chart is not None:
            chart, bundle, kind = self._chart, context.bundle, plan.kind

            def explorer_factory(on_tool):
                from ..context.source_retriever import get_source_retriever
                try:
                    retriever = get_source_retriever()
                except Exception:
                    log.exception("classics search unavailable for the explorer")
                    retriever = None
                tz = (chart.meta() or {}).get("timezone") or "Asia/Kolkata"
                return ChartExplorer(ChartTools(chart, tz, retriever), question, bundle,
                                     question_kind=kind, experience_mode=experience_mode,
                                     history=said, on_tool=on_tool)
        profile_context = context.bundle.get("profile_context") or {}
        return PrepareOutcome(prepared=PreparedRun(
            domain=routing.domain,
            intent=routing.intent,
            tense=routing.tense,
            agent=agent,
            bundle=context.bundle,
            context_used=context.context_used,
            profile_context_revision=profile_context.get("revision", 0),
            profile_context_as_of=profile_context.get("as_of"),
            question_kind=plan.kind,
            explorer_factory=explorer_factory,
            agent_factory=build_agent if explorer_factory else None,
            experience_mode=experience_mode,
        ))

    def _agent_run_and_verify(self, prepared: PreparedRun, messages: list) -> AgentRunResult:
        started = time.monotonic()
        result = self._generate_and_verify(prepared, messages)
        totals = getattr(prepared.agent, "usage_totals", lambda: {})() or {}
        # Two or more specialist calls means the single repair attempt ran.
        repaired = int(totals.get("calls") or 0) >= 2
        if prepared.explore_usage and totals:
            explore = prepared.explore_usage
            totals = {
                **totals,
                "calls": int(totals.get("calls") or 0) + len(explore),
                **{key: int(totals.get(key) or 0) + sum(int(u.get(key) or 0) for u in explore)
                   for key in ("input_tokens", "output_tokens", "cached_tokens")},
                "breakdown": [*explore, *(totals.get("breakdown") or [])],
            }
        result.usage = {
            **totals,
            "repaired": repaired,
            "latency_ms": int((time.monotonic() - started) * 1000),
        }
        return result

    def _generate_and_verify(self, prepared: PreparedRun, messages: list) -> AgentRunResult:
        try:
            reading = prepared.agent.run_structured_reading(messages)
        except Exception:
            log.exception("ask generation failed (domain=%s)", prepared.domain)
            return AgentRunResult(reading=None, violations=[], generation_failed=True)

        violations = self._check(prepared, reading)
        if not violations:
            return AgentRunResult(reading=reading, violations=[])

        # Exactly one repair attempt — hard cap, no open-ended retry loop.
        # D2: scoped when every surviving violation is attributable to a
        # field (`violation_fields()` excludes `None`), whole-object when
        # any isn't — the same fallback `Violation.field`'s own docstring
        # names: an unattributed violation means we don't know what's safe
        # to leave alone, so leave nothing alone, exactly today's behaviour.
        fields = violation_fields(violations)
        try:
            if None not in fields:
                repaired = self._scoped_repair(prepared, messages, reading, violations, fields)
            else:
                repaired = prepared.agent.run_structured_reading(messages + [{
                    "role": "user",
                    "content": (
                        "Your previous answer had these problems — answer again, fixing them, "
                        "using only what is in the CONTEXT BUNDLE: " + "; ".join(violations)
                    ),
                }])
        except Exception:
            log.exception("ask repair failed (domain=%s)", prepared.domain)
            return AgentRunResult(reading=None, violations=violations, generation_failed=True)
        reading = repaired

        violations = self._check(prepared, reading)
        if not violations:
            return AgentRunResult(reading=reading, violations=[])

        # The repair did not clear everything. What happens next depends on
        # WHICH violations survived, and the split is the whole point of
        # having severities: a death verdict or an invented citation must
        # never reach a reader, so those still discard the reading. A
        # coverage shortfall ("the D10 is never addressed") is a worse
        # reading, not a dangerous one — discarding it would hand the reader
        # an error instead of a good-but-incomplete consultation, which is a
        # strictly worse outcome for them.
        if safety_violations(violations):
            return AgentRunResult(reading=None, violations=violations)
        return AgentRunResult(reading=reading, violations=[],
                              quality_shortfall=quality_violations(violations))

    @staticmethod
    def _check(prepared: PreparedRun, reading: StructuredReading) -> list[str]:
        violations = (verify(reading, prepared.bundle, prepared.domain, prepared.tense)
                      + verify_coverage(reading, prepared.bundle))
        if prepared.experience_mode == "guided":
            violations += guided_violations(reading)
        return violations

    def _scoped_repair(self, prepared: PreparedRun, messages: list, original: StructuredReading,
                       violations: list[str], fields: set[str]) -> StructuredReading:
        """D2: ask for, and merge in, only the fields the surviving
        violations actually implicate — a tense violation confined to
        `interpretation` no longer costs a regenerated `technical_basis`
        alongside it.

        Merges onto `original` — the reading from before this repair
        attempt — not onto some other state — every field outside `fields`
        is by definition violation-free, so it is correct by construction
        to keep it untouched rather than ask the model to reproduce it.
        A field in `fields` the patch leaves as `None` (a provider that
        didn't fully comply with the narrowed schema) is left as
        `original`'s value too — the same "still parses, degrades to known
        behaviour" contract `run_structured_repair` documents; the
        violation simply survives into the re-verify below, exactly as it
        would have if this whole method didn't exist."""
        repair_messages = messages + [{
            "role": "user",
            "content": (
                f"Your previous answer had these problems in {', '.join(sorted(fields))} — "
                "answer again with ONLY those field(s), fixing them, using only what is in "
                "the CONTEXT BUNDLE: " + "; ".join(violations)
            ),
        }]
        patch = prepared.agent.run_structured_repair(repair_messages, fields)
        updates = {f: getattr(patch, f) for f in fields if getattr(patch, f, None) is not None}
        return original.model_copy(update=updates)

    def _log_cost(self, prepared: PreparedRun, status: str, thread_id: str | None) -> None:
        try:
            cost_log.info(json.dumps({
                "event": "ask.cost", "status": status, "domain": prepared.domain,
                "intent": prepared.intent, "question_kind": prepared.question_kind,
                "thread_id": thread_id,
                **_usage_summary(prepared.usage),
            }, default=str))
        except Exception:  # accounting never costs a reader their answer
            log.exception("ask cost log line failed")

    def _explore(self, prepared: PreparedRun) -> Iterator[dict]:
        """Run the exploring agent on a worker thread, yielding one status
        line per new kind of lookup while it works. On success the explored
        results join the bundle and the specialist is rebuilt over it; on any
        failure or timeout the turn carries on as the normal bundle path."""
        events: queue.Queue = queue.Queue()
        outcome: dict = {}
        started = time.monotonic()

        def work():
            try:
                explorer = prepared.explorer_factory(
                    lambda name, args: events.put(summarize_call(name, args)))
                outcome["result"] = explorer.explore()
                outcome["usage"] = list(explorer.usage_log)
            except Exception:
                log.exception("ask exploration failed (domain=%s)", prepared.domain)
            finally:
                events.put(None)

        thread = threading.Thread(target=work, name="ask-explore", daemon=True)
        thread.start()
        deadline = started + EXPLORE_TIMEOUT_S
        shown: set[str] = set()
        while True:
            try:
                label = events.get(timeout=max(0.1, deadline - time.monotonic()))
            except queue.Empty:
                log.warning("ask exploration timed out after %ss (domain=%s)",
                            EXPLORE_TIMEOUT_S, prepared.domain)
                return
            if label is None:
                break
            if label not in shown:
                shown.add(label)
                yield {"type": "status", "stage": "exploring", "label": label}

        found = outcome.get("result")
        prepared.explore_usage = outcome.get("usage") or []
        prepared.usage = {"explore_ms": int((time.monotonic() - started) * 1000)}
        if not found or not found.get("explored"):
            return
        bundle = prepared.bundle
        bundle["explored"] = found["explored"]
        if found.get("notes"):
            bundle["explorer_notes"] = found["notes"]
        if found.get("submitted"):
            bundle["rule_verdicts"] = found.get("verdicts") or {}
        if found.get("reader_facts"):
            bundle["reader_facts"] = found["reader_facts"]
        if found.get("overall"):
            bundle["overall_view"] = found["overall"]
        if found.get("weighing"):
            prepared.weighing = found["weighing"]
        if found.get("passages"):
            known = {p.get("chunk_id") for p in bundle.get("source_passages") or []}
            bundle["source_passages"] = [
                *(bundle.get("source_passages") or []),
                *(p for p in found["passages"] if p.get("chunk_id") not in known),
            ]
        prepared.agent = prepared.agent_factory(bundle)
        log.info("ask explored (domain=%s): %s", prepared.domain,
                 ", ".join(call.get("ref") or "" for call in found["explored"]))
        if "explored" not in prepared.context_used:
            prepared.context_used = [*prepared.context_used, "explored"]

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
        if prepared.explorer_factory is not None:
            yield from self._explore(prepared)
        yield {"type": "status", "stage": "interpreting",
              "label": f"{prepared.bundle.get('domain_name', prepared.domain)} specialist is interpreting…"}

        result = self._agent_run_and_verify(prepared, messages)
        if prepared.usage.get("explore_ms"):
            # The reader waited for the exploring step too.
            result.usage["latency_ms"] = (int(result.usage.get("latency_ms") or 0)
                                          + prepared.usage["explore_ms"])
        prepared.usage = result.usage

        if result.reading is None:
            status = "generation_failed" if result.generation_failed else "verification_failed"
            thread_id = persist(None, status)
            self._log_cost(prepared, status, thread_id)
            yield {
                "type": "done", "status": status, "schema_version": SCHEMA_VERSION,
                "domain": prepared.domain, "intent": prepared.intent,
                "tense": prepared.tense, "thread_id": thread_id,
                "usage": _usage_summary(result.usage),
            }
            return

        thread_id = persist(result.reading, "answered")
        self._log_cost(prepared, "answered", thread_id)
        yield {
            "type": "done", "status": "answered", "schema_version": SCHEMA_VERSION,
            "domain": prepared.domain, "intent": prepared.intent,
            "tense": prepared.tense,
            "context_used": prepared.context_used,
            "evidence_refs": [item.source for item in result.reading.technical_basis],
            # The exact ledger snapshot this answer was generated and
            # verified against — not re-read at persistence time. A later
            # correction/deletion to the ledger must never retroactively
            # change what an already-persisted answer is understood to have
            # been grounded in.
            "profile_context_revision": prepared.profile_context_revision,
            "profile_context_as_of": prepared.profile_context_as_of,
            "reading": result.reading.model_dump(),
            # The tool-using Ask's angle-by-angle weighing, shown under the
            # answer ("How we weighed it"). Absent on today's Ask.
            **({"weighing": prepared.weighing} if prepared.weighing else {}),
            "usage": _usage_summary(result.usage),
            # Present only when a quality check survived the repair attempt.
            # The reading shipped anyway (see AgentRunResult.quality_shortfall)
            # — this is what it fell short on, exposed rather than swallowed so
            # the miss rate is measurable instead of invisible. Not an error:
            # clients should treat it as telemetry, not something to show a
            # reader.
            **({"quality_shortfall": list(result.quality_shortfall)}
               if result.quality_shortfall else {}),
            "thread_id": thread_id,
        }
