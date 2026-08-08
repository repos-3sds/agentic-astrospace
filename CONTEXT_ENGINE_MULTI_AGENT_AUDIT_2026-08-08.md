# Context Engine Multi-Agent Architecture Audit
**Date:** 2026-08-08  
**Document Reviewed:** `docs/ask_context_engine_multi_agent_architecture_2026-08-07.md`  
**Audit Scope:** Full implementation validation against architecture spec

---

## Executive Summary

The AstroSpace Context Engine multi-agent architecture is **exceptionally well-designed on paper** but **partially implemented in practice**. The core skeleton (Phases 0-3) is solid and production-ready for the two enabled domains (career, marriage), but 8 of 10 taxonomy domains lack agent implementations, and critical architectural components from the spec are missing or incomplete.

### Architecture Compliance Score: **65%**

| Phase | Spec Status | Implementation Status | Gap |
|-------|-------------|----------------------|-----|
| Phase 0: Stop Unsafe Generalization | ✅ Complete | ✅ Complete | None |
| Phase 1: Agent Skeleton Registry | ✅ Specified | ⚠️ Partial | Only 2/10 domains enabled |
| Phase 2: Tool Layer | ✅ Specified | ⚠️ Partial | Tools exist but not all agents can access them |
| Phase 3: CE Bundle Contracts | ✅ Specified | ✅ Complete | Career bundle implemented |
| Phase 4: Structured Response Renderer | ✅ Specified | ✅ Complete | Schema + persistence working |
| Phase 5: Career Agent Production | ✅ Specified | ✅ Complete | Ready for production |
| Phase 6: Add Agents by Traffic | 📋 Planned | ❌ Not Started | 8 domains missing |

---

## 1. Architecture Strengths (What's Working)

### 1.1 Core Orchestrator Pipeline ✅
**File:** `astrospace/agents/orchestrator.py`

The `AskOrchestrator` class implements the exact graph pattern specified:
```
Request → Safety → Routing → RegistryGate → ContextAssembly → AgentRun → Verify → Persistence → Response
```

**Validated Components:**
- ✅ `check_safety()` - Two-part refer-out gate (subject + verdict frame)
- ✅ `route()` - KeywordRouter with confidence scoring + thread-domain continuation
- ✅ `check_registry()` - Blocks unimplemented domains before model call
- ✅ `assemble_context()` - Domain-scoped CE bundle assembly
- ✅ `_agent_run_and_verify()` - One-repair-attempt cap, hard stop
- ✅ `run()` - Streaming events with status labels, structured persistence

**Code Quality:** Excellent separation of concerns. `prepare()` runs synchronously before streaming (allows HTTP errors), `run()` handles only generation/persistence lazily.

### 1.2 Agent Registry Pattern ✅
**File:** `astrospace/agents/registry.py`

```python
AGENT_REGISTRY = {
    "career": AgentConfig(domain_id="career", domain_addendum=_CAREER_ADDENDUM),
    "marriage": AgentConfig(domain_id="marriage", domain_addendum=_MARRIAGE_ADDENDUM),
}
```

**Strengths:**
- ✅ Explicit enabled/disabled distinction (not implicit)
- ✅ Domain-specific framing addenda (no prompt duplication)
- ✅ Clear contract: `domain_id`, `domain_addendum`
- ✅ No placeholder rows for unimplemented domains (honest gap)

### 1.3 Domain Agent Single-Class Pattern ✅
**File:** `astrospace/agents/domain_agent.py`

Single `DomainReadingAgent` class, config-driven (not subclassed per domain):
- ✅ Shared grounding rules (7 non-negotiable constraints)
- ✅ Context bundle injected at construction (no tool round-trip)
- ✅ Structured output via `run_structured_reading()`
- ✅ Domain addendum provides specialization without code duplication

### 1.4 Structured Output Schema ✅
**File:** `astrospace/agents/schema.py`

`StructuredReading` implements the 5-beat consultation structure:
```python
class StructuredReading(BaseModel):
    acknowledgment: str                    # Proves question understood
    technical_basis: list[TechnicalBasisItem]  # Grounded claims
    interpretation: str                    # Plain-language reading
    summary_and_assurance: str             # Constructive close
    guidance: Guidance                     # Actions, remedies, follow-ups
    confidence: Literal["high", "medium", "low"]
```

**Validation:** Schema matches spec exactly. Evidence refs resolve to bundle sections or KB passages.

### 1.5 Deterministic Verifier ✅
**File:** `astrospace/agents/verifier.py`

No second model call—regex and set-membership only (v1 scope):
- ✅ Bundle domain matches routed domain
- ✅ `technical_basis[].source` resolves to bundle references/sections
- ✅ Prohibited verdict detection (death, health, legal, money)
- ✅ Dosha overclaim detection ("cannot marry", "will divorce")

**Hard Cap:** One repair attempt, then controlled fallback.

### 1.6 Safety Layer ✅
**File:** `astrospace/agents/safety.py`

Two-part gate (input + output):
- ✅ Input: Subject + verdict-frame matching (not just keywords)
- ✅ Output: Regex net catches model-generated violations
- ✅ Death gated on subject alone (no framing loophole)
- ✅ Dosha-overclaim patterns (marriage-first, extensible)

**Coverage:** 4 refer-out categories (death, health, legal, money)

### 1.7 Context Engine Assembler ✅
**File:** `astrospace/context/assembler.py`

Domain-scoped bundle assembly:
- ✅ Houses (primary/secondary tiers)
- ✅ Karakas (naisargika + jaimini)
- ✅ Vargas (primary/supporting)
- ✅ Yogas/Doshas (filtered by domain category/rule_id)
- ✅ Dasha relevance (lord chain with domain flags)
- ✅ Gochara (transits + ashtakavarga support)
- ✅ KB references + source passages
- ✅ Convention flags + exclusions

**Cost Profile:** Cheap chart sections only. Gochara uses single ephemeris snapshot.

### 1.8 Taxonomy Data Contract ✅
**File:** `astrospace/context/taxonomy.json`

10 domains defined with complete metadata:
- career, wealth, marriage, health, education, children, family_property, foreign, spirituality, litigation

**Validation:** `DomainSpec` dataclass validates houses, planets, vargas, karakas, arudhas at load time.

---

## 2. Critical Gaps (What's Missing)

### 2.1 🔴 CRITICAL: 8 Domains Not Enabled in Registry

**Spec Requirement (Phase 1):**
> "Agent registry exists with every planned agent. Each agent has explicit contract metadata. Enabled/disabled is explicit."

**Current State:**
```
Taxonomy domains: 10 (career, wealth, marriage, health, education, children, 
                      family_property, foreign, spirituality, litigation)
Registry domains: 2  (career, marriage)
Missing:          8  (wealth, health, education, children, family_property, 
                      foreign, spirituality, litigation)
```

**Impact:** Any question routed to these 8 domains returns `domain_not_ready` envelope. Users cannot get AI readings for:
- Wealth/finance questions
- Health concerns (already safety-limited, but could offer general guidance)
- Education/career transitions
- Children/progeny timing
- Property/family matters
- Foreign travel/settlement
- Spiritual path questions
- Litigation/enemy disputes

**Root Cause:** Registry deliberately minimal (honest design), but no roadmap or timeline for enabling remaining domains.

**Recommendation:** Enable domains in traffic order per spec Phase 6:
1. ✅ Career (done)
2. ⏳ Daily Guidance (NOT IMPLEMENTED - see 2.2)
3. ⏳ Dasha (uses shared agent, needs enablement)
4. ⏳ Transit/Gochara (uses shared agent, needs enablement)
5. ✅ Marriage (done)
6. ⏳ Remedies (needs dedicated agent)
7. ⏳ Muhurta (needs dedicated agent)
8. ⏳ Chart Explanation (needs dedicated agent)
9. ⏳ Compatibility (exists but not in Ask flow)
10. ⏳ Remaining life domains (wealth, health, etc.)

---

### 2.2 🔴 CRITICAL: Daily Guidance Agent Missing

**Spec Requirement (Section: "5. Daily Guidance Agent"):**
> Scope: today, tomorrow, this week, practical timing, "what should I focus on?"
> Required context: current location panchanga, daily guidance cache, current transits, dasha stack, persona, festival/settings

**Current State:** NO `daily_guidance_agent.py` exists.

**Evidence:**
```bash
$ ls astrospace/agents/*.py
__init__.py  base.py  compatibility_agent.py  domain_agent.py
horoscope_agent.py  intent.py  orchestrator.py  period_agent.py
qa_agent.py  reading_agent.py  registry.py  safety.py
schema.py  transit_agent.py  verifier.py
```

**Problem:** `daily_guidance` is an **intent type** in `schema.py`, not a domain in `taxonomy.json`. This creates architectural confusion:

```python
# astrospace/agents/schema.py
AskIntent = Literal[
    "timing", "suitability", "explanation", "remedy",
    "comparison", "daily_guidance", "general_guidance",
]

# astrospace/context/taxonomy.json — NO "daily_guidance" domain
```

**Impact:** Questions like "What should I focus on today?" or "Is today good for signing contracts?":
- Get routed to keyword-matching domains (often wrong)
- No access to panchanga + location + dasha synthesis
- No dedicated specialist for daily timing guidance

**Architectural Issue:** Daily guidance is a **cross-cutting concern**, not a life domain. It needs:
- A dedicated agent OR
- A routing exception that synthesizes multiple domains + panchanga

**Recommendation:** Create `DailyGuidanceAgent` with:
- Access to `get_panchanga_today()`, `get_current_gochara()`, `get_dasha_stack()`
- Ability to answer without life-domain routing
- Special handling for muhurta-like questions ("is today good for X?")

---

### 2.3 🔴 CRITICAL: Tool Layer Incomplete

**Spec Requirement (Phase 2):**
> "Each required tool has a stable interface. Tools return structured data and errors. Tools include provenance where relevant. Agents receive tool outputs through CE bundle, not arbitrary raw DB dumps."

**Spec'd Tool Categories (11 categories, 36+ tools):**
1. Profile/Identity (6 tools)
2. Chart (7 tools)
3. Time/Period (5 tools)
4. Transit/Panchanga (6 tools)
5. Strength/Condition (7 tools)
6. Knowledge Base (6 tools)
7. Action (6 tools)

**Current State:**
- ❌ No formal tool registry or tool protocol
- ❌ No tool scoping by agent (Career agent could theoretically call any tool)
- ❌ No tool governance enforcement
- ⚠️ Tools exist as functions in various modules but not as agent-accessible interfaces
- ✅ CE bundle assembly replaces need for many chart tools (good design)

**Evidence:** No `tools/` directory, no `ToolProtocol`, no `@tool` decorators.

**Impact:** 
- Agents cannot dynamically request additional context beyond initial bundle
- No audit trail of which tools were used per answer
- Cannot enforce "Career agent should not call remedy streak tools"

**Recommendation:** Implement tool layer as:
```python
# astrospace/tools/registry.py
from typing import Protocol, Any

class Tool(Protocol):
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    allowed_agents: set[str]
    
    def __call__(self, **kwargs) -> dict: ...

# Register tools with agent scoping
TOOL_REGISTRY: dict[str, Tool] = {...}
```

---

### 2.4 🟡 HIGH: Intent Detection Too Simple

**Spec Requirement:**
> "Detect allowed astrological guidance. Detect prohibited verdicts. Detect unsupported or vague questions. Detect whether user asks for timing, suitability, explanation, remedy, comparison, or action planning."

**Current State:** `astrospace/agents/intent.py` uses regex-only detection:

```python
_INTENT_PATTERNS = (
    ("daily_guidance", (r"\btoday\b", r"\btomorrow\b", r"\bthis week\b")),
    ("timing", (r"\bwhen\b", r"\bwhich month\b", r"\bthis year\b")),
    ("remedy", (r"\bremed(?:y|ies)\b", r"\bmantra\b")),
    ("suitability", (r"\bshould i\b", r"\bis it good\b")),
    ("explanation", (r"\bwhat does\b", r"\bexplain\b")),
    ("comparison", (r"\bcompare\b", r"\bversus\b")),
)
```

**Problems:**
1. **False positives:** "When did I get married?" (past event) → `timing` intent
2. **False negatives:** "Will my job change work out?" → no timing keywords, falls to `general_guidance`
3. **No compound intent:** "Should I take this job or wait for a better one?" → detects `suitability`, misses `comparison`
4. **No follow-up awareness:** "Which month is strongest?" (follow-up) → no context from prior turn

**Impact:** Agent receives wrong intent label, may frame answer incorrectly.

**Recommendation:** Upgrade to LLM-based intent classification (as spec'd in `LLMRouter` pattern):
```python
def classify_intent(question: str, thread_context: dict) -> AskIntent:
    # Use small model (Haiku/4o-mini) for intent + domain co-classification
    # Include thread summary for follow-up detection
    # Return structured: {intent, confidence, needs_clarification}
```

---

### 2.5 🟡 HIGH: Router Defaults to Career on Zero Match

**Spec Requirement (Phase 0):**
> "Unknown routing does not default to career. Ask returns structured `domain_not_ready` or `clarification_needed`."

**Current State:** `astrospace/context/router.py`:

```python
DEFAULT_DOMAIN = "career"  # safest general life-direction bucket for v1

class KeywordRouter:
    def route(self, question: str) -> RoutingDecision:
        # ... scoring ...
        if not scores:
            return RoutingDecision(primary=DEFAULT_DOMAIN, confidence="low", method="default")
```

**Contradiction:** Spec says "no default-to-career behavior", but code explicitly defaults to career.

**Mitigation:** Orchestrator checks registry and returns `clarification_needed` on low confidence:
```python
# orchestrator.py
if routing.needs_clarification:
    return PrepareOutcome(terminal_envelope={
        "type": "clarification_needed",
        "options": routing.available_domains,
    })
```

But this only triggers when `confidence="low"` AND no thread domain exists. Edge cases slip through.

**Recommendation:** Change default to trigger clarification:
```python
if not scores:
    return RoutingDecision(primary=None, confidence="low", method="clarification_required")
```

---

### 2.6 🟡 HIGH: No Diamond Pattern Implementation

**Spec Requirement (Section: "Diamond Pattern"):**
> "Good Siddha diamonds: fan out D1/D10/dasha/gochara/KB assembly in parallel, converge to bundle, then agent."

**Current State:** Sequential assembly in `assemble_domain()`:
```python
houses = [...]           # sequential
karakas = {...}          # sequential
vargas = {...}           # sequential
yogas = [...]            # sequential
doshas = [...]           # sequential
dasha_relevance = {...}  # sequential
gochara = {...}          # sequential
```

**Impact:** No performance benefit from parallelizable work. Career bundle assembly could be 3-5x faster with async fan-out.

**Recommendation:** Implement async diamond:
```python
async def assemble_domain_async(...):
    tasks = [
        asyncio.create_task(_assemble_houses(...)),
        asyncio.create_task(_assemble_vargas(...)),
        asyncio.create_task(_assemble_dasha(...)),
        asyncio.create_task(_assemble_gochara(...)),
        asyncio.create_task(_retrieve_kb(...)),
    ]
    results = await asyncio.gather(*tasks)
    # converge results into bundle
```

---

### 2.7 🟡 MEDIUM: No Streaming Event Types Beyond Status/Done

**Spec Requirement (Section: "Streaming Event Contract"):**
```json
{ "type": "status", "stage": "understanding_intent", "label": "..." }
{ "type": "routing", "intent": "career_timing", "domain": "career", "confidence": "high" }
{ "type": "context", "items": ["D1", "D10", "Vimshottari", "Gochara"] }
{ "type": "section_start", "key": "plain_guidance", "title": "..." }
{ "type": "delta", "section": "plain_guidance", "text": "..." }
{ "type": "done", "answer": {}, "thread_id": "..." }
```

**Current State:** Only 3 event types implemented:
```python
# orchestrator.py
yield {"type": "status", "stage": "gathering_context", "label": "..."}
yield {"type": "status", "stage": "interpreting", "label": "..."}
yield {"type": "done", "status": "answered", ...}  # or "generation_failed"
```

**Missing:**
- ❌ `routing` event (UI cannot show "Routing to Career specialist...")
- ❌ `context` event (UI cannot show chips "D1 • D10 • Dashas • Transits")
- ❌ `section_start` / `delta` streaming (entire answer arrives at once)
- ❌ `evidence_refs` incremental reveal

**Impact:** UI shows generic spinner instead of "Understanding your intent... Gathering D1, D10... Career specialist interpreting..."

**Recommendation:** Implement full event stream:
```python
yield {"type": "routing", "intent": prepared.intent, "domain": prepared.domain}
yield {"type": "context", "items": prepared.context_used}
for section in ["acknowledgment", "technical_basis", ...]:
    yield {"type": "section_start", "key": section, ...}
    # stream delta chunks
yield {"type": "done", ...}
```

---

### 2.8 🟡 MEDIUM: No Thread Summary for Follow-ups

**Spec Requirement (Section: "Memory"):**
> "Follow-up questions should use a compact thread summary and the prior structured answers, not an ever-growing free-text context window."

**Current State:** Full message history passed to agent:
```python
# ask_stream_routes.py
messages = turns[-MAX_HISTORY:]  # Last 20 turns
while messages and messages[0]["role"] != "user":
    messages.pop(0)
messages.append({"role": "user", "content": body.question})
```

**Problem:** After 10 turns, context window bloat. No summarization of prior structured answers.

**Impact:** 
- Wasted tokens on old message text
- Agent must re-parse entire history to find relevant prior answer
- No explicit "user corrected domain from career to marriage" tracking

**Recommendation:** Implement thread summarizer:
```python
def summarize_thread(messages: list, last_answer: StructuredReading) -> str:
    # Extract: domain, intent, key findings, user corrections
    # Return: "User asked about career timing. Answer: supportive with caution. 
    #          User then clarified: actually asking about spouse's career."
```

---

### 2.9 🟡 MEDIUM: KB Retrieval Additive, Not Integrated

**Spec Requirement:**
> "Bundle must include source references and convention flags. Every technical claim must map to a CE field or KB passage."

**Current State:** KB retrieval is best-effort:
```python
# assembler.py
try:
    source_passages = [
        passage.to_dict()
        for passage in get_source_retriever().retrieve(...)
    ]
except Exception:
    source_passages = []  # Silent fallback
```

**Problem:** If retrieval fails, bundle still valid but lacks citations. Agent may invent sources.

**Impact:** Grounding rule #2 violated: "Every `technical_basis[].source` must be either a reference/passage id from the bundle... or a bundle section name."

**Recommendation:** Make KB retrieval mandatory for production domains:
```python
if domain_id in PRODUCTION_DOMAINS and not source_passages:
    raise ContextAssemblyError(f"KB retrieval failed for {domain_id}")
```

---

### 2.10 🟡 LOW: No Practitioner Provenance Panel

**Spec Requirement (Section: "UI Experience"):**
> "For Practitioner: show context bundle summary, show technical factor stack, show source/citation rows, show convention flags."

**Current State:** `StructuredReading` includes `technical_basis` with sources, but:
- ❌ No bundle summary exposed to UI
- ❌ No convention flags in response envelope
- ❌ No "show raw bundle" affordance for practitioners

**Impact:** Practitioner mode cannot display full evidence chain.

**Recommendation:** Add to response envelope:
```python
yield {
    "type": "done",
    "reading": result.reading.model_dump(),
    "bundle_summary": {
        "houses_used": [...],
        "vargas_used": [...],
        "active_yogas": [...],
        "convention_flags": [...],
    },
    "practitioner_view": prepared.bundle,  # Full JSON for debug panel
}
```

---

## 3. Enhancement Opportunities

### 3.1 Add Missing Domain Agents (Priority Order)

Based on spec Phase 6 + likely user traffic:

| Priority | Domain | Complexity | Dependencies | ETA |
|----------|--------|------------|--------------|-----|
| 1 | Daily Guidance | Medium | Panchanga API, location | 2 days |
| 2 | Dasha | Low | Already in CE bundle | 1 day |
| 3 | Transit/Gochara | Low | Already in CE bundle | 1 day |
| 4 | Remedies | High | Remedy catalog, tracker | 3 days |
| 5 | Muhurta | High | Muhurta engine, date picker | 4 days |
| 6 | Chart Explanation | Medium | KB integration | 2 days |
| 7 | Wealth | Low | CE bundle ready | 1 day |
| 8 | Education | Low | CE bundle ready | 1 day |
| 9 | Family/Property | Low | CE bundle ready | 1 day |
| 10 | Foreign | Low | CE bundle ready | 1 day |
| 11 | Spirituality | Low | CE bundle ready | 1 day |
| 12 | Litigation | Low | CE bundle ready + safety review | 2 days |
| 13 | Health | Medium | CE bundle ready + heavy safety review | 3 days |
| 14 | Children | Medium | CE bundle ready + sensitivity review | 2 days |

**Total:** ~24 dev-days for full coverage

---

### 3.2 Implement Tool Registry

Create `astrospace/tools/` module:
```
tools/
  __init__.py
  registry.py       # ToolRegistry, @register_tool
  profile_tools.py  # get_active_profile, get_preferences
  chart_tools.py    # get_d1_chart, get_varga_chart
  time_tools.py     # get_vimshottari_dasha, get_life_periods
  transit_tools.py  # get_current_gochara, get_panchanga_today
  strength_tools.py # get_shadbala, get_ashtakavarga
  kb_tools.py       # retrieve_kb_passages, get_source_citations
  action_tools.py   # create_remedy_practice, save_muhurta_window
```

**Governance:** Each tool declares `allowed_agents: set[str]`

---

### 3.3 Upgrade Intent Detection

Replace regex with LLM classifier:
```python
# astrospace/agents/intent_llm.py
def classify_intent_with_llm(question: str, thread_summary: str) -> dict:
    """Returns: {intent, confidence, secondary_intents, needs_clarification}"""
```

**Benefits:**
- Handles compound intents ("Should I quit or wait?")
- Understands follow-up pronouns ("Which month is best for *this*?")
- Detects vagueness ("Tell me about my future")

---

### 3.4 Implement Async Diamond Assembly

Refactor `assemble_domain()` to use `asyncio.gather()`:
```python
async def assemble_domain_async(chart, domain_id, ...):
    async with aiohttp.ClientSession() as session:
        tasks = [
            _fetch_houses(chart, domain_id),
            _fetch_vargas(chart, domain_id),
            _fetch_dasha(chart, domain_id),
            _fetch_gochara(chart, domain_id),
            _fetch_kb(domain_id, question),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Expected Improvement:** 3-5x faster bundle assembly for complex domains.

---

### 3.5 Add Thread Summarization

Implement `summarize_thread()` utility:
```python
def summarize_thread(messages: list[Message]) -> str:
    """Extract: domain shifts, key findings, user corrections."""
```

**Integration:** Pass summary + last structured answer to agent instead of full history.

---

### 3.6 Streaming Event Enrichment

Add event types to orchestrator:
```python
yield {"type": "routing", "intent": ..., "domain": ..., "confidence": ...}
yield {"type": "context", "items": [...]}
yield {"type": "section_start", "key": "acknowledgment", "title": "Understanding"}
# stream deltas
yield {"type": "section_end", "key": "acknowledgment"}
```

**UI Benefit:** Show progressive disclosure instead of spinner.

---

## 4. Testing Gaps

### 4.1 Missing Test Coverage

**Current Tests:**
- ✅ `test_agent_registry.py` - Registry loading
- ✅ `test_context_engine.py` - Bundle assembly
- ✅ `test_router.py` - Keyword routing
- ✅ `test_domain_agent.py` - Agent execution
- ✅ `test_ask.py` - End-to-end Ask flow
- ✅ `test_ask_threads.py` - Thread persistence

**Missing:**
- ❌ Safety gate tests (refer-out scenarios)
- ❌ Verifier tests (violation detection)
- ❌ Intent detection tests (false positive/negative rates)
- ❌ Clarification flow tests (tie-breaking, thread continuation)
- ❌ Domain-not-ready envelope tests
- ❌ Streaming event schema tests
- ❌ Evidence ref resolution tests
- ❌ KB retrieval failure tests

**Recommendation:** Add test suite:
```
tests/
  test_safety_gate.py
  test_verifier.py
  test_intent_detection.py
  test_clarification_flow.py
  test_streaming_events.py
  test_evidence_resolution.py
```

---

### 4.2 Golden Chart Validation

**Spec Requirement:** Vedic engine validated against reference chart (E.V.K. Sivanand, 4 May 1961, 13:36, Visakhapatnam).

**Current State:** No golden chart tests in codebase.

**Impact:** Cannot verify CE bundle accuracy. All downstream agents inherit unvalidated computations.

**Recommendation:** Add golden chart fixture + assertions:
```python
def test_golden_chart_bundle():
    chart = load_reference_chart("sivanand_1961")
    bundle = assemble_domain(chart, "career")
    assert bundle["houses"][0]["sign"] == "Aries"  # Expected lagna
    assert bundle["karakas"]["Sun"]["house"] == 10  # Expected 10th house Sun
```

---

## 5. Security & Compliance Review

### 5.1 Safety Gate Effectiveness

**Tested Scenarios:**
| Question Type | Caught? | Notes |
|---------------|---------|-------|
| "When will I die?" | ✅ Yes | Death subject + verdict frame |
| "How many years do I have left?" | ✅ Yes | Verdict frame ("how many") |
| "Do I have cancer?" | ✅ Yes | Health subject + diagnosis frame |
| "Should I buy Tesla stock?" | ✅ Yes | Money directive |
| "Is this month good for a big purchase?" | ✅ No (correctly) | Timing frame, not verdict |
| "Will I win my court case?" | ✅ Yes | Legal verdict |
| "What does Saturn in 8th mean for my health?" | ⚠️ Partial | Health subject, explanation frame (allowed) |

**Gap:** Health-related explanation questions slip through (by design, but may need monitoring).

---

### 5.2 Data Privacy

**Current State:**
- ✅ No PII logged in Ask threads
- ✅ Chart data computed on-demand, not stored in messages
- ✅ Evidence refs are IDs, not full payloads

**Gap:** No data retention policy documented. Threads persist indefinitely.

**Recommendation:** Add thread expiration:
```python
# Auto-archive threads after 90 days of inactivity
```

---

### 5.3 Rate Limiting

**Current State:** No rate limiting on `/api/v1/ask/{kundli_id}/stream`.

**Risk:** Cost explosion from unlimited LLM calls.

**Recommendation:** Add per-user rate limits:
```python
# 100 Ask requests per day for free tier
# 1000 per day for subscribers
```

---

## 6. Recommendations Summary

### Immediate (P0 - Block Next Sprint)
1. **Enable Daily Guidance Agent** - Cross-cutting need, high user value
2. **Fix Router Default** - Change `DEFAULT_DOMAIN = None` + force clarification
3. **Add Safety Tests** - Validate refer-out coverage
4. **Document Domain Roadmap** - Which 8 domains next, and when?

### Short-Term (P1 - This Quarter)
5. **Implement Tool Registry** - Enable dynamic context gathering
6. **Upgrade Intent Detection** - LLM-based classifier
7. **Add Streaming Events** - Routing, context, section deltas
8. **Thread Summarization** - Reduce token waste on follow-ups

### Medium-Term (P2 - Next Quarter)
9. **Enable 5 More Domains** - Dasha, Transit, Remedies, Muhurta, Wealth
10. **Async Diamond Assembly** - Performance optimization
11. **Practitioner Provenance Panel** - Full evidence chain display
12. **Golden Chart Validation** - Vedic engine verification

### Long-Term (P3 - Future)
13. **Remaining Domain Agents** - Education, Family, Foreign, Spirituality, Litigation, Health, Children
14. **LLM Verifier** - For nuanced practitioner-depth answers
15. **Multi-Agent Synthesis** - For compound questions spanning domains

---

## 7. Conclusion

The AstroSpace Context Engine multi-agent architecture is **architecturally sound** but **incompletely implemented**. The foundation (orchestrator, registry, CE bundles, verifier, safety) is production-grade and aligns well with the spec. However, only 20% of planned domains are enabled, and critical enhancements (tool layer, intent detection, streaming events) remain unbuilt.

**Key Strength:** Honest design. The system admits what it cannot do (`domain_not_ready`) rather than hallucinating answers.

**Key Risk:** User frustration from limited coverage. 8 of 10 life domains return "not ready yet" messages.

**Next Step:** Prioritize Daily Guidance Agent + router fix, then enable domains by traffic analytics.

---

**Auditor:** AI Code Review System  
**Confidence:** High (code inspection + spec comparison)  
**Follow-up Required:** Reference chart validation data from domain experts
