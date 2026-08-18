# Siddha Ask + Context Engine Multi-Agent Architecture Plan

Date: 2026-08-07. Last reviewed: 2026-08-08.

Status: living architecture doc — vision plus real implementation state, not
a point-in-time audit. The body below (Executive Position through the
Addendum) is the original plan, unedited except where noted; it should still
be read as *target*, not as a description of running code. The
"Implementation Status" section immediately below it, and the "Update
2026-08-08" section near the end, are what's actually true right now. When
the gap between vision and code changes, edit those two sections in place —
do not fork a new dated file for the next pass; that's how this repo stops
being readable (see CLAUDE.md).

## Product Context

Siddha is a mobile-first Vedic life guidance app. It is not meant to be just
an astrology chart viewer or a generic AI chatbot. The product vision is to
become a daily way-of-life guide that helps users understand timing,
self-patterns, relationships, work, remedies, rituals, calendar choices, and
personal growth through a grounded Vedic Context Engine.

Ask is the conversational doorway into that system. Its job is to translate a
human life question into the right astrological domain, gather deterministic
chart and time context, interpret it with a specialist agent, verify that the
answer is grounded, and return guidance that is practical, humane, and
appropriate to the user's persona.

### Vision

- Siddha should feel like a disciplined consultation, not a free-form bot.
- The Context Engine computes; agents interpret; deterministic verification
  protects trust.
- Guided users should receive simple, supportive language. Balanced users
  should see enough reasoning to trust the answer. Practitioner users should
  get deeper technical context, citations, and chart links.
- Every meaningful answer should be traceable to chart computation, curated
  knowledge, domain rules, safety policy, and user profile context.

### Scope

This architecture covers the Ask + Context Engine path:

- routing a user question to the correct life domain and intent
- gating unsupported domains honestly
- assembling deterministic CE bundles
- running configured domain specialist agents
- verifying structured output before persistence
- streaming progress and final answers to the mobile UI
- preserving thread continuity and follow-up behavior

This document does not replace the separate mobile UI design plan, knowledge
ingestion plan, or core astrology computation checklists. It defines how those
systems should be orchestrated when a user asks Siddha a question.

### Business Objective

The business goal is to make Siddha trustworthy enough for repeat daily use
and deep enough to justify a premium guidance experience. Ask should increase
engagement across the app by connecting answers to Today, Dashas, Calendar,
Yantra, Charts, Remedies, Muhurta, and future domain journeys. The architecture
must therefore prioritize accuracy, provenance, safety, latency control,
persona fit, and extensibility over superficial chatbot breadth.

## Implementation Status (as of 2026-08-08)

### Live in code

- **AskOrchestrator** (`astrospace/agents/orchestrator.py`) implements the
  Addendum's graph below almost exactly: `SafetyResult -> RoutingResult ->
  RegistryResult -> ContextResult -> AgentRunResult`, one class, sequential
  method calls, no LangGraph or other graph-runtime dependency. Split into
  `prepare()` (safety, routing, registry gate, context assembly — everything
  that can short-circuit to a terminal envelope or a normal HTTP error,
  called before the SSE stream opens) and `run()` (the generator: model
  call, verify, one repair attempt, persist).
- **Registry** (`astrospace/agents/registry.py`) — `AGENT_REGISTRY` holds
  exactly two of the eleven agents mapped out below: `career` and
  `marriage`. Every other domain in the Agent Map returns `domain_not_ready`,
  never a silent generic fallback. Phase 0's acceptance criteria are met.
- **Structured output** (`astrospace/agents/schema.py`) — `StructuredReading`
  covers acknowledgment / technical_basis / interpretation /
  summary_and_assurance / guidance / confidence: the "Human-Readable Flow"
  below, collapsed from 6 steps to 5 (`context_gathered` and
  `technical_interpretation` merged into one `technical_basis` list;
  `next_paths.app_links` wasn't built). Envelope fields (`domain`, `status`,
  `intent`, `schema_version`) are computed server-side and never trusted to
  the model, per grounding rule #10 below.
- **Deterministic verifier** (`astrospace/agents/verifier.py`) — no second
  model call. Checks domain match, every `technical_basis[].source`
  resolving to a real bundle reference or section, `prohibited_verdict`, and
  `dosha_overclaim_kind`. Covers part of the Grounding Tests below (citation
  validity, prohibited/dosha claims); "no unsupported dasha/transit claims"
  (grounding rule #3) is not checked yet — see the Update section.
- **Repair loop** is exactly the "structured output repair loop" specified
  below: one attempt, hard-capped, in
  `AskOrchestrator._agent_run_and_verify()`.
- **Context assembly** — `assemble_domain()` (`astrospace/context/`) is the
  Phase 3 CE bundle assembler, fully deterministic and taxonomy-driven. It
  is **not** intent-aware: a "timing" question and an "explanation" question
  about career currently get an identical bundle.
- **Intent detection** (`astrospace/agents/intent.py`) — `detect_intent()`
  is live and server-computed, but its output is a label only. It tags the
  response; it does not yet shape what context gets assembled or gate
  anything.
- **Routing** (`astrospace/context/router.py`) — `KeywordRouter`: deterministic
  keyword scoring with tie-detection for clarification, not the LLM-based
  router this document originally implied. Thread continuity
  (`thread_domain`, so a pronoun follow-up doesn't re-clarify) and an
  explicit reader override (`domain_override`, bypassing the router entirely
  when a clarification chip is tapped) were added 2026-08-08 as real
  production bug fixes — see the Update section.
- **Streaming events** are close to the "Streaming Event Contract" below:
  `status`, `clarification_needed`, `domain_not_ready`, `refer_out`, `done`.
  No `section_start`/per-field `delta` — the structured answer is delivered
  whole once verification passes, not streamed field by field.

### Explicitly not built

- **Tool layer** (Phase 2, "Tool Architecture" below) — zero tools.
  `DomainReadingAgent` never calls anything; the full bundle is handed to it
  up front, and it answers with one forced `deliver_reading` tool call. This
  is a deliberate, current decision, not an oversight not-yet-reached — see
  the Update section for why a "give the agent scoped tools" proposal was
  considered and rejected for now.
- **Context Planner node** doesn't exist as a component. `assemble_domain`
  plays this role today, but statically per-domain, not per-intent.
- **9 of the 11 planned agents** — Clarifier, Daily Guidance, Dasha,
  Transit, Remedies, Muhurta, Chart Explanation, Compatibility, and Safety
  as a distinct node — are still sections in this document, not code.
  "Safety" is a function (`agents/safety.py`), not an agent:
  `check_safety()` gates before routing, matching this document's
  safety-first intent even though it was never built as its own node.
- **Multi-domain synthesis / diamond patterns** are not built. A question
  naming two configured domains currently asks for clarification rather
  than fanning out and converging — a real, currently-unresolved conflict
  with the synthesis idea below; see the Update section.
- **Persona depth rendering** (Guided/Balanced/Practitioner technical
  stack) — `StructuredReading` has one fixed depth. Persona-based rendering
  is a UI-only concern right now (the Why-sheet's mode selector swaps a
  description string, not a different backend payload).

## Executive Position

Siddha Ask should not be a generic astrology chatbot. It should be a Context Engine-led, tool-grounded, multi-agent guidance system where every answer is traceable to deterministic chart computation, relevant knowledge-base passages, domain rules, safety policy, and the user's persona.

The current risk is architectural: if one specialist agent is wired and unsupported domains fall back to a generic model, the product gives the illusion of complete astrological coverage without the grounding, guardrails, or domain responsibility needed to earn trust. That must stop before expanding Ask.

The right approach is:

1. Build a robust skeleton for every agent first.
2. Define tool access, context contracts, KB scope, safety rules, and output schema before generation.
3. Enable agents one by one based on product traffic and confidence.
4. Never silently fall back from an unsupported specialist to a generic answer.

## Product Principle

Ask should behave like a panel of disciplined astrologers, not one model pretending to know everything.

Each answer should show that Siddha:

- understood the user's intent,
- gathered the correct chart and life-context inputs,
- interpreted those inputs through an appropriate domain lens,
- translated the interpretation into humane language,
- acknowledged uncertainty and tradition/convention limits,
- guided the next useful action, follow-up, remedy, or screen.

## End-to-End Ask Flow

Every Ask request should move through this sequence:

1. **Input Capture**
   - Raw user question.
   - Active kundli/profile.
   - Persona: Guided, Balanced, Practitioner.
   - Language and voice/text mode.
   - Thread history if follow-up.
   - Current location when question depends on panchanga, today, transit, or muhurta.

2. **Intent + Safety Classification**
   - Detect allowed astrological guidance.
   - Detect prohibited verdicts: death/longevity, diagnosis, emergency medical, legal directive, financial directive, crisis/self-harm.
   - Detect unsupported or vague questions.
   - Detect whether user asks for timing, suitability, explanation, remedy, comparison, or action planning.

3. **Domain Routing**
   - Route to one primary domain.
   - Attach secondary domains only when genuinely needed.
   - If confidence is low, route to Clarifier Agent.
   - If domain specialist is not enabled, return an honest specialist-unavailable response.
   - No default-to-career behavior.
   - No generic fallback for unsupported domains.

4. **Tool-Based Context Gathering**
   - Agent does not invent context.
   - Orchestrator or agent tools gather deterministic data from FastAPI/internal tools/MCP-style tools:
     - chart data,
     - varga data,
     - dashas,
     - gochara/transits,
     - panchanga,
     - muhurta windows,
     - remedies catalog,
     - KB passages,
     - user preferences,
     - prior thread memory.

5. **Context Engine Assembly**
   - CE converts raw data into an agent-ready context bundle.
   - Bundle must contain only relevant factors for the domain.
   - Bundle must identify missing context.
   - Bundle must include source references and convention flags.

6. **Agent Response Generation**
   - Agent receives:
     - intent,
     - safety classification,
     - CE bundle,
     - scoped KB passages,
     - persona tone settings,
     - thread summary/history,
     - output schema.
   - Agent must answer only within its responsibility boundary.

7. **Verifier / Guardrail Pass**
   - Validate response schema.
   - Check no forbidden claims.
   - Check technical claims reference CE fields or KB passages.
   - Check answer belongs to routed domain.
   - Check tone/persona rules.
   - If failed, regenerate once or return controlled fallback.

8. **Persistence + UI Rendering**
   - Save structured answer, not just markdown text.
   - Save context snapshot IDs/evidence refs.
   - UI renders schema sections directly.
   - Thread history reopens without retriggering generation.

## Agent Skeleton

Every agent should have the same skeleton before any domain is launched.

### Agent Contract

Each agent must define:

- `agent_id`
- `agent_name`
- `enabled`
- `owned_domains`
- `secondary_domains_allowed`
- `allowed_intents`
- `disallowed_intents`
- `required_context`
- `optional_context`
- `tool_access`
- `kb_scope`
- `persona_depth_rules`
- `output_schema`
- `guardrail_rules`
- `handoff_rules`
- `fallback_behavior`

### Agent Runtime Inputs

```json
{
  "request": {
    "question": "Is there a job change this year?",
    "input_mode": "text",
    "language": "en",
    "persona": "balanced"
  },
  "routing": {
    "intent": "career_timing",
    "primary_domain": "career",
    "secondary_domains": ["dasha", "transit"],
    "confidence": "high",
    "safety_class": "allowed"
  },
  "context": {
    "bundle_id": "ctx_...",
    "chart_layers": ["D1", "D10"],
    "dasha_stack": true,
    "gochara": true,
    "kb_passages": true,
    "missing_context": []
  },
  "thread": {
    "thread_id": "ask_...",
    "summary": "User is asking about job timing.",
    "recent_turns": []
  }
}
```

## Structured Output Pattern

Every response should follow a consistent Siddha pattern, independent of agent.

### Human-Readable Flow

1. **Acknowledge Intent**
   - Name what the user is really asking.
   - Example: "You're asking whether the current year supports a career transition, not just general work pressure."

2. **Context Gathered**
   - State the context used.
   - Example: "I looked at your D1 career houses, D10 career chart, current Vimshottari dasha, and the current gochara affecting career houses."

3. **Technical Interpretation**
   - Explain the core astrological reasoning.
   - Practitioner gets more detail; Guided gets simplified terms.
   - Must cite CE fields and KB passages.

4. **Plain-Language Prediction / Guidance**
   - Translate into natural, empathetic language.
   - Avoid deterministic overclaiming.
   - Focus on useful decision framing.

5. **Summary + Assurance**
   - Short answer.
   - Confidence level.
   - What is supportive, mixed, or cautionary.

6. **Next Paths**
   - Follow-up questions.
   - Relevant app screens.
   - Remedies/practices if appropriate.
   - Timing window exploration.

### Machine Schema

```json
{
  "answer_id": "ans_...",
  "agent_id": "career_work_agent",
  "status": "answered",
  "intent_acknowledgement": {
    "detected_intent": "career_timing",
    "user_facing_text": "You're asking whether this year supports a job change."
  },
  "context_gathered": {
    "summary": "D1, D10, Vimshottari dasha, and gochara were used.",
    "items": [
      {
        "label": "D1 career houses",
        "context_ref": "ce.domains.career.houses"
      },
      {
        "label": "D10 career chart",
        "context_ref": "ce.domains.career.vargas.D10"
      }
    ],
    "missing": []
  },
  "technical_interpretation": [
    {
      "title": "Dasha timing",
      "body": "The active dasha stack connects to career and gains indicators.",
      "evidence_refs": ["ce.dasha.current", "kb.career.dasha.001"]
    }
  ],
  "plain_guidance": {
    "headline": "A change is supported, but best handled with preparation.",
    "body": "This is a better period for planned movement than impulsive resignation."
  },
  "summary": {
    "verdict": "supportive_with_caution",
    "confidence": "medium",
    "one_line": "Explore opportunities, but keep practical safeguards in place."
  },
  "next_paths": {
    "follow_up_questions": [
      "Which month is strongest?",
      "What does the D10 say about role type?"
    ],
    "app_links": [
      {
        "label": "View Dashas",
        "route": "/m/dashas"
      },
      {
        "label": "View Transits",
        "route": "/m/yantra/transits"
      }
    ],
    "remedies": []
  },
  "safety": {
    "class": "allowed",
    "notes": []
  },
  "rendering": {
    "guided_depth": "short",
    "balanced_depth": "standard",
    "practitioner_depth": "technical"
  }
}
```

## Tool Architecture

When we say MCP tools here, we mean agent-accessible deterministic tools. They may be implemented as FastAPI services, internal Python tool functions, LangGraph tools, or MCP-hosted tools. The important requirement is not the transport; it is that agents use tools instead of memory or improvisation.

### Tool Categories

#### Profile / Identity Tools

- `get_active_profile`
- `get_profile_birth_details`
- `get_user_preferences`
- `get_persona_settings`
- `get_current_location`
- `get_thread_memory`

#### Chart Tools

- `get_d1_chart`
- `get_varga_chart`
- `get_all_vargas`
- `get_planetary_positions`
- `get_house_lords`
- `get_bhava_chalit`
- `get_special_lagnas`

#### Time / Period Tools

- `get_vimshottari_dasha_stack`
- `get_yogini_dasha_stack`
- `get_chara_dasha_stack`
- `get_life_periods`
- `get_dasha_interpretation_context`

#### Transit / Panchanga Tools

- `get_current_gochara`
- `get_transit_context`
- `get_panchanga_today`
- `get_calendar_day_context`
- `get_location_based_panchanga`
- `get_month_calendar_intelligence`

#### Strength / Condition Tools

- `get_shadbala`
- `get_ashtakavarga`
- `get_vimshopaka_bala`
- `get_planetary_conditions`
- `get_yogas`
- `get_doshas`
- `get_jaimini_factors`

#### Knowledge Base Tools

- `retrieve_kb_passages`
- `retrieve_domain_rules`
- `retrieve_source_citations`
- `retrieve_remedy_traditions`
- `retrieve_muhurta_rules`
- `retrieve_safety_policy`

#### Action Tools

- `create_remedy_practice`
- `start_mantra_streak`
- `save_muhurta_window`
- `create_calendar_reminder`
- `open_app_route`
- `archive_ask_thread`

### Tool Governance

Tools must be scoped by agent.

Career Agent should not call remedy streak tools unless handing off to Remedies Agent.

Muhurta Agent should not call compatibility tools unless a relationship/marriage muhurta explicitly needs compatibility context.

Safety Agent should not call chart tools for prohibited verdicts; it should classify and redirect.

## Agent Map

### 1. Router Agent

Purpose:
- Convert raw question into intent, domain, confidence, and safety class.

Must use:
- taxonomy,
- intent examples,
- safety policy,
- enabled-agent registry.

Must not:
- answer astrology.

Output:
- routing decision only.

### 2. Clarifier Agent

Purpose:
- Ask one clean question when user intent is vague or context is missing.

Examples:
- "Are you asking about timing, suitability, or what to prepare?"
- "Is this for your current job, a new role, or business?"

Must not:
- produce chart predictions.

### 3. Career & Work Agent

Scope:
- job change,
- promotion,
- business role,
- workplace pressure,
- public status,
- income from work where framed as career timing.

Required context:
- D1: 10th, 6th, 2nd, 11th, 7th when business/clients,
- D10,
- current dasha stack,
- gochara to career houses/lords,
- relevant yogas/doshas,
- bala/condition for career planets,
- career KB.

Guardrails:
- no directive resignation advice,
- no guarantee of job,
- no financial investment advice,
- no fatalistic career verdict.

### 4. Relationship & Marriage Agent

Scope:
- marriage timing,
- relationship dynamics,
- spouse indicators,
- compatibility guidance,
- communication timing.

Required context:
- D1: 7th, 2nd, 4th, 5th, 8th,
- D9,
- Venus/Jupiter/Moon condition,
- dasha relevance,
- gochara to 7th/Venus/Jupiter,
- compatibility data if partner exists,
- relationship KB.

Guardrails:
- no deterministic "divorce will happen",
- no coercive advice,
- no moral judgment,
- no harmful relationship directive.

### 5. Daily Guidance Agent

Scope:
- today,
- tomorrow,
- this week,
- practical timing,
- "what should I focus on?"

Required context:
- current location panchanga,
- daily guidance cache,
- current transits,
- dasha stack,
- current persona,
- festival/context settings.

Guardrails:
- chart at birth place only for natal factors,
- current location for daily panchanga,
- no major life verdict from a single day signal.

### 6. Dasha Agent

Scope:
- mahadasha,
- antardasha,
- pratyantar,
- sookshma,
- prana,
- period effects,
- period transitions.

Required context:
- full dasha tree,
- natal placement of dasha lords,
- house ownership,
- dignity,
- yogas/doshas involving lords,
- transits modifying the period,
- dasha KB.

Guardrails:
- period is a climate, not destiny,
- must explain level hierarchy,
- must distinguish natal promise from timing trigger.

### 7. Transit / Gochara Agent

Scope:
- current movement,
- 30/90-day signals,
- transit impact,
- "what is moving now?"

Required context:
- current transit positions,
- natal reference from Lagna and Moon,
- active dasha stack,
- ashtakavarga where relevant,
- gochara rules KB.

Guardrails:
- no isolated transit verdict,
- always explain whether transit is activating natal promise or merely describing pressure.

### 8. Remedies Agent

Scope:
- practices,
- mantras,
- vrata,
- offerings,
- color/gem/prayer guidance,
- streaks,
- audio practice.

Required context:
- reason for remedy,
- active dasha/transit/dosha/yoga,
- remedy catalog,
- tradition/source,
- suitability and contraindications,
- user practice preference.

Guardrails:
- no paid fear-based remedy,
- no guarantee that remedy "removes" karma,
- no gemstone directive without caution,
- no tracking for one-time offerings unless the practice is repeatable.

### 9. Muhurta Agent

Scope:
- event timing,
- date/range windows,
- griha pravesha,
- upanayana,
- marriage-related timing,
- signing,
- journey,
- venture start,
- property/gold.

Required context:
- location panchanga,
- date range,
- event-specific muhurta rules,
- tithi,
- nakshatra,
- weekday,
- yoga,
- karana,
- tara bala,
- chandra bala,
- rahu/yamaganda/gulika,
- excluded intents.

Guardrails:
- if user selects "something else", classify intent first,
- if event lacks rule support, use general panchanga only and say so,
- no muhurta for medical/legal/financial verdicts.

### 10. Chart Explanation Agent

Scope:
- "what does this placement mean?",
- yoga/dosha explanation,
- varga explanation,
- house/planet/nakshatra meaning.

Required context:
- exact placement,
- relevant chart layer,
- source KB,
- user persona.

Guardrails:
- explain, do not predict beyond the factor.

### 11. Safety / Boundary Agent

Scope:
- prohibited or high-stakes topics.

Required context:
- safety policy,
- user question,
- optional domain label.

Must not:
- use chart tools to answer prohibited questions.

Output:
- supportive refusal,
- safe alternative,
- emergency/help guidance when needed.

## Domain Enablement Sequence

We should build skeletons for all agents first, then enable answer generation one by one.

### Phase 0: Stop Unsafe Generalization — DONE

Acceptance criteria:
- Unsupported domain does not fall back to generic answer.
- Unknown routing does not default to career.
- Ask returns structured `domain_not_ready` or `clarification_needed`.
- UI renders those states cleanly.

### Phase 1: Agent Skeleton Registry — DONE for 2 of 11 agents (career, marriage)

Acceptance criteria:
- Agent registry exists with every planned agent.
- Each agent has explicit contract metadata.
- Enabled/disabled is explicit.
- Router checks registry before dispatch.
- Tests prove disabled agents cannot answer.

### Phase 2: Tool Layer — NOT STARTED, deliberately deferred (see Update below)

Acceptance criteria:
- Each required tool has a stable interface.
- Tools return structured data and errors.
- Tools include provenance where relevant.
- Agents receive tool outputs through CE bundle, not arbitrary raw DB dumps.

### Phase 3: CE Bundle Contracts — DONE for career + marriage; not intent-aware

Acceptance criteria:
- Domain-specific bundle schema exists.
- Career bundle is implemented first.
- Missing-context behavior is explicit.
- Evidence refs are stable IDs that UI can display.

### Phase 4: Structured Response Renderer — DONE

Acceptance criteria:
- Frontend renders structured answer sections.
- No regex parsing of LLM markdown for core layout.
- Ask History stores and reopens structured answers.
- Follow-ups preserve thread continuity.

### Phase 5: Career Agent Production Readiness — DONE (marriage shipped alongside it)

Acceptance criteria:
- Career agent uses D1 + D10 + dasha + gochara + KB.
- Answers pass schema validation.
- Claims are grounded to CE refs.
- Safety verifier runs after generation.
- Persona variants render correctly.

### Phase 6: Add Agents by Traffic — IN PROGRESS, 2 of 10 shipped

**Correction, 2026-08-08:** the original order below mixed life-domain agents
with technique/product-feature items (Daily Guidance, Dasha, Transit,
Remedies, Muhurta, Chart Explanation) — but the Addendum two sections above
already established that dasha/gochara/panchanga/vargas/remedies/muhurta are
evidence providers and product features, not top-level agents. The corrected
list below matches the real domain catalog (`astrospace/context/taxonomy.py`,
10 domains) rather than the earlier mixed list. Daily Guidance, Chart
Explanation, and the technique modules remain real product surfaces — they
just aren't sequenced here as "agents to add," because they aren't agents.

Recommended order (✅ = shipped 2026-08-08):

1. ✅ Career
2. ✅ Marriage (shipped alongside Career, not after — traffic data to
   re-justify this order doesn't exist yet; see the Update section's note on
   instrumenting before expanding)
3. Wealth
4. Children
5. Health
6. Foreign / relocation
7. Education
8. Family property
9. Spirituality
10. Litigation (safety-sensitive; mature guardrails first)

## Backend Architecture Recommendation

Introduce an Ask Orchestrator service.

```text
AskStreamRoute
  -> AskOrchestrator
      -> SafetyClassifier
      -> IntentRouter
      -> AgentRegistry
      -> ContextPlanner
      -> ToolExecutor / CEAssembler
      -> AgentRunner
      -> ResponseVerifier
      -> ThreadPersistence
```

The route should not decide fallback behavior inline. The route should only:

- authenticate,
- validate request,
- call orchestrator,
- stream structured events,
- map errors.

## Streaming Event Contract

Streaming should move away from plain deltas only.

Recommended events:

```json
{ "type": "status", "stage": "understanding_intent", "label": "Understanding your question" }
{ "type": "routing", "intent": "career_timing", "domain": "career", "confidence": "high" }
{ "type": "context", "items": ["D1", "D10", "Vimshottari", "Gochara"] }
{ "type": "section_start", "key": "plain_guidance", "title": "What this means" }
{ "type": "delta", "section": "plain_guidance", "text": "..." }
{ "type": "done", "answer": {}, "thread_id": "..." }
```

This lets UI show the Context Engine working instead of a mysterious spinner.

## UI Experience

Ask should show:

- "Understanding your intent..."
- "Gathering D1, D10, Dashas, Transits..."
- "Career specialist is interpreting..."
- then structured answer.

For unsupported domains:

- "This Siddha specialist is not ready yet."
- "You can still explore Today, Chart, Dashas, or ask a Career question."

For vague questions:

- show one clarification question,
- do not generate a vague reading.

For Practitioner:

- show context bundle summary,
- show technical factor stack,
- show source/citation rows,
- show convention flags.

## Grounding Rules

Agents must obey these rules:

1. Every technical claim must map to a CE field or KB passage.
2. No invented placements.
3. No unsupported dasha/transit claims.
4. No contradiction of computed chart data.
5. No general fallback when domain is unavailable.
6. No deterministic fatalism.
7. No paid/remedial fear framing.
8. No medical/legal/financial directive.
9. No "certainty" language unless deterministic computation supports the statement.
10. Every answer must expose what context was used.

### Enforcement status (added 2026-08-08 — which of the above is real code, not just principle)

| # | Rule | Enforced by | Status |
|---|------|-------------|--------|
| 1 | Claims map to CE field/KB passage | `verifier.py::verify()`, `_valid_sources()` | **Enforced** |
| 2 | No invented placements | Structurally impossible — the model never computes placements, `assemble_domain` does, and the agent has no way to state one that isn't in its own prompt | **Enforced by construction** |
| 3 | No unsupported dasha/transit claims | — | **Aspirational.** This is Item 3 above (temporal-claim checking), not built |
| 4 | No contradiction of computed chart data | Same mechanism as #2 — the bundle is the only source of chart facts the model has | **Enforced by construction** |
| 5 | No general fallback when domain unavailable | `AskOrchestrator.check_registry()` → `domain_not_ready` | **Enforced** |
| 6 | No deterministic fatalism | `safety.py::dosha_overclaim_kind()`, checked in `verify()` | **Enforced, narrow** — see the paraphrase-evasion note in Item 3 above; catches the phrases in its table, unverified against paraphrase |
| 7 | No paid/remedial fear framing | Domain-addendum prompt text only (`registry.py`) | **Prompt-only, no net** — the gap named in Item 3 above (`remedy_overclaim_kind()` doesn't exist yet) |
| 8 | No medical/legal/financial directive | `safety.py::refer_out_kind()` (input) + `prohibited_verdict()` (output) | **Enforced, both directions** |
| 9 | No unsupported certainty language | — | **Aspirational**, same gap as #3 (Item 3's "confidence vs. evidence strength" check) |
| 10 | Every answer exposes context used | `context_used` field, computed server-side in `orchestrator.assemble_context()` | **Enforced** |

Six of ten are real code today; two are structural guarantees rather than
checks (nothing to build, the architecture makes the violation impossible);
two are named gaps already tracked in the Update section above. This table
is the honest current answer to "which of our guardrails are load-bearing
and which are still just intentions" — keep it in sync as Item 3 lands.

## Testing Matrix

### Routing Tests

- career question routes career.
- marriage question routes relationship.
- vague question routes clarifier.
- unsupported domain returns unavailable.
- health diagnosis routes safety.
- investment directive routes safety.
- death/longevity routes safety.

### Grounding Tests

- career answer cites D10 when making profession claim.
- dasha answer cites current dasha level.
- transit answer cites transit window.
- remedy answer cites reason and tradition.
- muhurta answer cites panchanga components.

### Conversation Tests

- fresh question creates one thread.
- follow-up appends to same thread.
- opening history does not regenerate.
- archived thread disappears from active history.
- structured answer reopens exactly as saved.

### Persona Tests

- Guided: short, plain, action-oriented.
- Balanced: plain answer + reasoning.
- Practitioner: technical factor stack + citations.

## Immediate Backlog

### P0 — DONE

- ~~Remove generic fallback for unsupported routed domains in mobile Ask streaming.~~
- ~~Remove `career` as default domain for unknown questions.~~
- ~~Add structured unsupported-domain and clarification responses.~~

### P1 — DONE

- ~~Create Agent Registry with enabled/disabled status.~~ (2 of 11 agents defined, not all — registry pattern itself is done)
- Define agent contracts for all planned agents. — not done past career/marriage
- ~~Define structured response schema and validator.~~
- ~~Persist structured response payload in Ask messages.~~

### P2 — DONE

- ~~Implement Ask Orchestrator service.~~
- ~~Implement Career CE bundle contract.~~ (marriage too)
- ~~Implement Career Agent with verifier.~~ (marriage too)
- ~~Update frontend renderer for structured answer cards.~~

### P3 — partially done

- ~~Add streaming status events.~~
- Add context-used chips. — backend emits `context_used`; not yet surfaced as UI chips
- Add practitioner provenance panel. — not built (see Persona depth rendering, above)
- Add UI affordance to choose/refine context for follow-up. — not built

### P4 — next, superseded by the 2026-08-08 revised sequence below

The original plan's next backlog item was "add agents by traffic." The
2026-08-08 three-way design review (this document's Update section, next)
revised that: strengthen and instrument the verifier before adding either
more agents or more agent capability, because two production bugs shipped
today (thread-continuity routing, a clarification-chip loop) both came from
the routing layer having less rigor than the generation layer already has.
Treat the Update section below as the current P4, not this paragraph.

## Final Recommendation

Do not expand Ask by adding more prompts directly into the route.

First build:

- agent registry,
- routing contract,
- CE bundle contracts,
- tool contracts,
- structured output schema,
- guardrail verifier.

Then enable agents one by one.

Siddha's credibility will come from this discipline: the user should feel that a real astrologer gathered the right context before speaking, and that the system knows when not to speak.

## Addendum: Agents, Loops, And Graphs Applied To Siddha

The "Agents, Loops, Graphs" framing is useful, but only if we apply it with restraint.

For Siddha Ask:

- **Agents** are bounded specialists that own a life-domain or product intent.
- **Loops** live inside one bounded specialist when it needs to gather/check a little more context.
- **Graphs** orchestrate the full Ask flow: safety, routing, context assembly, agent execution, verification, persistence, and UI rendering.

The architecture should not become "many agents talking to many agents." That would be noisy, slow, hard to debug, and astrologically fragmented. The better model is:

```text
Ask Orchestrator = graph
Domain specialist = agent
Agent tool use = bounded loop
Context Engine modules = deterministic graph/tool nodes
Verifier = separate checker node
```

### Agent

An agent is appropriate when judgment, language, prioritization, or synthesis is needed.

In Siddha:

- Career Agent interprets career questions.
- Marriage Agent interprets relationship questions.
- Remedies Agent interprets practice/remedy guidance.
- Muhurta Agent interprets event-timing requests.
- Clarifier Agent asks the one missing question.
- Safety Agent declines or redirects prohibited requests.

Astrological techniques are not top-level agents by default.

Not agents:

- Dasha
- Gochara
- Panchanga
- Vargas
- Ashtakavarga
- Shadbala
- Yogas
- Doshas

These are evidence providers inside the Context Engine. They feed agents; they do not compete with agents.

### Loop

A loop is appropriate only when the system has:

- a clear stop condition,
- a check that can fail,
- a hard attempt limit,
- no need for human judgment mid-run.

Allowed loops in Siddha Ask:

1. **Agent tool loop**
   - Agent may call at most 1-3 scoped tools if the CE bundle is insufficient.
   - Example: Career Agent asks for D10 details or a dasha window.
   - Hard stop: max tool calls reached or context sufficient.

2. **Structured output repair loop**
   - If model output fails JSON/schema validation, regenerate once with the exact validation errors.
   - Hard stop: one repair attempt, then controlled fallback.

3. **Citation repair loop**
   - If `evidence_refs` do not resolve, ask the model to remove or replace invalid refs once.
   - Hard stop: one repair attempt.

Loops that should not exist:

- endless "improve answer" loops,
- agent self-review loops with no external check,
- repeated retrieval loops until the model feels satisfied,
- loops that write to DB/action tools repeatedly.

### Graph

The Ask orchestrator should be a graph because the flow has real gates and branches.

Recommended graph:

```text
RequestNode
  -> SafetyNode
  -> IntentRouterNode
  -> AgentRegistryNode
      -> ClarifierNode              if low confidence
      -> DomainNotReadyNode         if domain unsupported
      -> ContextPlannerNode         if supported
          -> CEAssemblerNode
          -> DomainAgentNode
          -> DeterministicVerifierNode
              -> RepairNode         if schema/ref validation fails once
              -> PersistenceNode    if valid
              -> ResponseNode
```

### Diamond Pattern

The diamond pattern is useful where multiple independent context checks can run in parallel and then converge.

Good Siddha diamonds:

```text
Career question
  -> fan out:
      - assemble D1 career factors
      - assemble D10 career factors
      - assemble dasha relevance
      - assemble gochara relevance
      - retrieve career KB passages
  -> converge:
      - career CE bundle
  -> Career Agent
```

```text
Marriage question
  -> fan out:
      - assemble D1 relationship factors
      - assemble D9 factors
      - assemble dasha relevance
      - assemble gochara relevance
      - retrieve marriage KB passages
  -> converge:
      - marriage CE bundle
  -> Marriage Agent
```

Bad diamonds:

- running several astrology agents in parallel for the same question before routing is clear,
- asking Dasha Agent, Transit Agent, Yoga Agent, and Career Agent separately and synthesizing prose,
- parallel calls that duplicate the same chart computation without cache/shared snapshot.

### Checker Node

The checker must not be the same generation context grading itself.

For v1, use a deterministic checker:

- schema validates,
- required fields exist,
- `evidence_refs` resolve against CE bundle or KB results,
- output domain equals routed domain,
- unsupported domain did not answer,
- prohibited verdict regex passes,
- dosha/remedy fatalism regex passes.

Only later add an LLM verifier, and only for high-risk practitioner-depth answers where deterministic checks are insufficient.

### Memory

Ask memory should be explicit:

- thread messages,
- thread summary,
- routing history,
- context bundle IDs,
- structured answer payloads,
- user corrections such as "I meant marriage, not career."

Do not rely on raw chat transcript alone. Follow-up questions should use a compact thread summary and the prior structured answers, not an ever-growing free-text context window.

### Revised Implementation Bias

Build the "boring graph" first.

Do not start with parallel multi-agent synthesis. Start with inspectable nodes:

1. Safety.
2. Routing.
3. Registry.
4. Context planning.
5. CE bundle.
6. One domain agent.
7. Deterministic verifier.
8. Persistence.

Then add loops only where a real failure mode demands them.

Then add diamonds only where independent context work can actually run in parallel.

## Update 2026-08-08: Design Review After the First Two Agents Shipped

Career and marriage went live, then broke twice in production — a follow-up
question with no domain keywords of its own re-triggered clarification
instead of continuing the thread, and tapping a clarification chip
("career") sent the same ambiguous question back through the router
prefixed with "Answer this as a Career question:", which added no
disambiguating signal (the router only checks whether a keyword is
*present*, not how many times) and produced an infinite, compounding loop
of the identical clarification. Both fixes are live
(`AskOrchestrator.route()`'s `thread_domain` and `domain_override`
parameters, `astrospace/agents/orchestrator.py`). Both bugs came from the
same root cause: the routing layer had noticeably less rigor than the
generation layer already had, because this document's Phase 3–5 work went
straight into grounding the *answer* without a matching pass on grounding
the *route*. That prompted a three-way design review (this session, a
collaborating agent session in the same repo, and the person driving both)
on what to build next. This section is the outcome — read it as the current
plan of record, superseding "Phase 6: add agents by traffic" and the
original P4 as the immediate next step.

### ADR-001: No tool access for domain reading agents — REJECTED, DECIDED 2026-08-08

Early in the review, giving `DomainReadingAgent` a small set of scoped tools
(`get_domain_bundle`, `get_varga_chart`, `get_dasha_window`,
`get_transit_context`, `retrieve_kb_passages` — essentially a subset of the
"Tool Architecture" section above) was proposed as the next step, on the
theory that 5 scoped tools is safer than the 35+ tools this document
originally mapped out.

That's true as far as it goes, but it was still the wrong next step, and the
reasoning for rejecting it is worth keeping on record because it will come
up again: **`DomainReadingAgent` having zero tools is not a gap to close, it
is the load-bearing property that makes the deterministic verifier work at
all.** Today, `assemble_domain()` builds the entire context bundle before
the model ever sees the question, and `verify()` checks every
`technical_basis[].source` against that one, already-known bundle. If the
model could instead call tools to fetch its own context mid-generation, the
bundle stops being fixed and known in advance, and the verifier would also
have to validate which tool calls were legitimate for the question — a much
harder, much less deterministic problem. It would also resurrect exactly
the failure mode this whole rebuild exists to fix: the *previous* Ask
implementation, `VedicQAAgent` (still live on the non-streaming `/ask`
path, with real tools — `get_birth_chart`, `get_varga_chart`,
`get_today_panchanga`, `get_current_gochara`), is a free-form tool-calling
agent, and free-form tool access is what produced answers that looked
confident but weren't reliably grounded — the original trust problem in
this document's Executive Position.

**The kept principle, worth stating plainly because it's now been
independently rediscovered twice in one review:**

> The model does not decide what astrological facts exist. The backend
> decides the domain, the chart layers that matter, the dashas/transits/
> yogas/references that are relevant, and what evidence is admissible. The
> agent only interprets the bundle it's handed.

If a tool layer gets built later (Phase 2 above), it should be tools the
*orchestrator* calls deterministically to assemble a bundle — never tools
the model selects and invokes itself.

### The revised near-term sequence

In priority order, each scoped down from what was originally floated in
review to something concretely buildable against the code as it exists
today:

1. **Instrument before strengthening.** Nothing currently logs *which*
   `verify()` violation fired or how often repair triggers —
   `verification_failed`/`generation_failed` only ever surface as an SSE
   status. Log violation types server-side first. Deciding which of the
   verifier checks below are worth building should be driven by what
   actually happens in production, not by guessing.
2. **Give the SSE stream an error contract — no verified path today.**
   Confirmed by reading `generate()` in `ask_stream_routes.py`: the success
   loop (`for event in orchestrator.run(...): yield _sse(event)`) has no
   `try`/`except` around it at all. The only exception handling anywhere in
   the pipeline is the two `except Exception` blocks inside
   `_agent_run_and_verify()`, scoped specifically to the model call. Anything
   else that throws mid-generator — a DB write failure in `persist_prepared`,
   a bug in `_sse()`'s encoding — kills the SSE connection with whatever
   bytes already went out: no `done` frame, no error frame, client left
   hanging. Add a `fatal_error` event type and wrap `generate()`'s loop so
   every stream is guaranteed to end in *some* terminal frame. Small, cheap,
   and worth doing before verifier or planner work, not after — those add
   more code inside the generator, which is more surface for this exact gap.
3. **Strengthen the verifier**, cheapest checks first:
   - "required sections present per intent" — mostly free, since
     `StructuredReading`'s Pydantic schema already guarantees every field
     exists; the remaining piece is intent-specific *content* requirements
     (e.g. a `timing` intent should probably have a non-empty
     `follow_up_questions`), not structural presence.
   - "no unsupported dasha/transit claims" (grounding rule #3, never
     implemented) — the hard one. It means extracting date/month
     expressions from free text (a real answer already says things like
     "through mid-September 2026") and cross-checking them against
     `dasha_relevance`'s actual windows. Scope the first cut narrowly:
     require any month/year mentioned in the answer to appear somewhere in
     the bundle's serialized dasha data, rather than attempting general
     temporal-claim parsing.
   - **Re-audit `dosha_overclaim_kind`/`prohibited_verdict` for the exact
     weakness `refer_out_kind` already found and fixed in itself.**
     `safety.py`'s own comment records that whole-phrase matching "let 24 of
     31 probe questions through... because an allowlist of sentences cannot
     cover paraphrase," which is why `refer_out_kind` moved to two-part
     subject+frame matching. `dosha_overclaim_kind` and `prohibited_verdict`
     are still simple phrase-regex tables — `test_verifier.py`'s existing
     parametrized cases confirm the regexes catch the phrases *in* the
     table, but nothing confirms they survive paraphrase the way refer-out's
     redesign was specifically built to. Worth the same treatment, not a new
     mechanism — this is the project re-applying a lesson it already
     learned once, not a novel gap.
4. **Make `assemble_domain` intent-aware — this *is* the Context Planner
   from Phase 3/the graph above, not a new component.** ~~`detect_intent()`
   already runs server-side and is already threaded through
   `PreparedRun.intent`; it just isn't used to shape what gets assembled
   yet, only to label the response.~~ **DONE, 2026-08-18 — see "Update
   2026-08-18" below.** `assemble_domain` now takes `intent=...` and trims
   per-planet decorative texture for a scoped set of intents. Deliberately
   a first increment, not the full target below: no top-level section
   (`timeline`, `gochara`, `retrospect`) is dropped by intent yet — only
   `_planet_brief`'s texture is. If an LLM-driven planner is ever
   warranted beyond that, its output must be schema-validated with a
   deterministic fallback to the full taxonomy-defined bundle on failure —
   never trusted un-checked, per the kept principle above. Target signature:
   `ContextEngine.assemble(domain, intent, profile_id, question,
   thread_context) -> CEBundle` — `assemble_domain` growing an `intent`
   parameter, not a new class.

   **Dependency this creates for Item 3 (the verifier), not obvious until
   this is actually built:** today the bundle is always full, so the
   verifier only has to catch *over*-claiming — a citation to something not
   in the bundle. The moment the bundle gets trimmed per-intent,
   *under*-provisioning becomes possible, and `verify()` has no way to see
   it — it only checks that a citation resolves to something present, never
   that something the answer needed was missing. A too-narrow trim would be
   invisible to every check in this document. Ship intent-aware trimming
   and a bundle-completeness sanity check in the same change, or trimming
   quietly regresses grounding without any test catching it.
5. **Resolve routing vs. synthesis semantics before building either
   further.** This is a real, currently-open conflict, not just a future
   nice-to-have: "Is this a good time for my career and my marriage?" is
   the literal test case `_needs_clarification()` uses today to define
   *ambiguous* — mentioning two configured domains is exactly what forces a
   clarify right now. Multi-domain synthesis (the diamond pattern above)
   would make that same phrase answer both instead. Those are incompatible
   readings of the same signal, so before any synthesis work starts, the
   router needs two named categories, not one tie-break rule:
   - **Ambiguous** — "Is this a good time?" with no named domain: clarify.
   - **Multi-domain** — both named domains are in `AGENT_REGISTRY` and
     ready: fan out, assemble both bundles, converge on a synthesis node.
   - A domain named that isn't registered yet needs a partial-answer path
     ("I can speak to career; marriage isn't ready yet") rather than either
     silently dropping it or refusing the whole question.

   **Stated interim policy, until the above is built:** a multi-domain
   question is a clarification, full stop — that's today's actual behavior,
   and it's being named here as a deliberate stated policy rather than left
   as an unstated side effect of the tie-break rule. Add a test that asserts
   this explicitly (e.g. `test_multi_domain_question_clarifies_until_synthesis_ships`)
   so the day synthesis lands, the diff that changes this behavior is
   obvious and intentional, not a silent regression of an assumption nobody
   wrote down.
6. **Section-targeted repair, scoped down from "regenerate just the failed
   field."** The original idea (repair message says exactly
   `technical_basis[1].source is invalid` instead of a generic "answer
   again, fixing these problems") is worth doing and is a small change to
   `_agent_run_and_verify()`'s corrective message — `verify()` already
   returns fairly specific per-violation strings, this is about surfacing
   them precisely rather than newly generating them. Actually regenerating
   only the failed field while holding the rest of the structured object
   fixed is a bigger, separate protocol change (partial-object patching
   against a single forced tool call) and should stay explicitly out of
   scope until the simpler message-precision version proves insufficient.
7. **Explicit node contracts, no LangGraph.** Convert the orchestrator's
   already-typed dataclasses (`SafetyResult`, `RoutingResult`, etc.) into a
   uniform per-node contract (e.g. a `Protocol` with one `run(state) ->
   Result` shape) once there are enough nodes that the informal version
   gets hard to follow. Low urgency at 2 agents; revisit once agent count or
   node count grows enough to justify it — not before, per this repo's
   general bias against premature abstraction.

Everything above should run **after** fixing one documentation gap in the
"Backend Architecture Recommendation" and graph diagrams elsewhere in this
document: they list the pipeline starting at routing/intent
(`IntentRouterNode` / `RouterNode` first). The real, correct, and currently
implemented order is **safety first, unconditionally, before routing** —
`AskOrchestrator.prepare()` calls `check_safety()` before `route()`, so a
death/health/legal/money question never reaches the router at all. Any
future diagram or plan should keep Safety as the first node, not fold it in
after routing for narrative convenience.

### What stays out of scope until the above lands

- No LangGraph or other graph-runtime dependency (Item 6 above is a
  contract-shape change, not a runtime change).
- No tool access for domain agents (see "the proposal that was rejected,"
  above) — if a deterministic, orchestrator-owned tool layer is built per
  Phase 2, it's still the orchestrator calling tools, never the model.
- No expansion past career + marriage (Phase 6) until the routing layer has
  the same rigor as the generation layer already does — repeating Phase 6
  before Items 1–4 above would very likely ship a third and fourth agent on
  top of the same routing gaps that produced the two bugs that triggered
  this review.

## Cross-Check: Codex's 2026-08-08 Draft (`Codex_Architecture_Draft.md`)

A parallel draft was written independently and largely converges with the
above — same current-state read, same rejected-tool-access reasoning, same
ambiguous-vs-multi-domain distinction. Rather than keep two documents, the
items below are what that draft had and this one didn't; each was checked
against the real code before being folded in, not merged on trust.

**Genuine gaps, now incorporated:**

- **Verifier needs a "confidence vs. evidence" check.** Not in `verify()`
  today (confirmed by reading `astrospace/agents/verifier.py`): nothing
  checks that a `confidence: "high"` reading is actually backed by more than
  one or two thin citations. Add to Item 2's list above, after the cheap
  checks — it's a comparison against the reading's own `technical_basis`
  length/quality, not new external data, so it should be cheap too.
- **"Remedies framed as paid removal" has no deterministic net.** Confirmed
  by reading `astrospace/agents/safety.py` in full: there is no
  `_REMEDY_OVERCLAIM` table analogous to `_DOSHA_OVERCLAIM_OUTPUT`. This
  non-negotiable (CLAUDE.md: "Remedies are traditional practice, never 'pay
  to remove'") currently exists only as prompt instruction in each domain's
  `domain_addendum` string — exactly the state dosha-overclaim was in before
  this session added its regex net (the comment already in `safety.py`
  says as much: "had only a prompt instruction, no net"). Add a
  `remedy_overclaim_kind()` alongside `dosha_overclaim_kind()` — same
  shape, same file — as part of Item 2.
- **Concrete per-intent context lists**, useful as the literal target for
  Item 3 (making `assemble_domain` intent-aware) rather than describing it
  only abstractly:
  - Career + timing: D1, D10, 10th house/lord, 6th/2nd/11th supporting
    houses, Vimshottari dasha stack, relevant gochara, career references.
  - Marriage + timing: D1, D9, 7th house/lord, Venus/Jupiter/Mars,
    2nd/4th/8th/12th supporting houses, dasha relevance, gochara, marriage
    references, dosha flags with caution rules.
- **A worked agent-contract example**, not just field names. The original
  "Agent Contract" section (under Agent Skeleton, near the top of this
  document) lists field names as prose; a concrete filled-in example for
  `career` — `agent_id`, `owned_domains`, `allowed_intents`,
  `required_context_by_intent`, `disallowed_outputs`, `persona_depth`,
  `fallback_behavior: domain_not_ready` — is worth keeping as the literal
  template once Item 1 (explicit node contracts) or agent count past 2
  makes a formal registry worth building. See `Codex_Architecture_Draft.md`
  §"Agent Contract Template" for the full YAML; not duplicated here since
  the source file isn't going away.

**Discrepancy worth resolving, not yet resolved:** Codex's draft lists 8
primary intents including `follow_up`; the live `AskIntent` type
(`astrospace/agents/schema.py:15`) has exactly 7 — `timing`, `suitability`,
`explanation`, `remedy`, `comparison`, `daily_guidance`,
`general_guidance` — no `follow_up`. This isn't an oversight to silently
fix either way: today, "this is a follow-up" is handled structurally (the
`thread_domain` continuity mechanism in `AskOrchestrator.route()`), not as
an intent label. Whether a follow-up should *also* carry its own intent
value (e.g. so the verifier or UI can treat it differently) is an open
question, not a settled one — decide it explicitly before Item 3's
intent-aware context planning gets built, since that's the point where the
intent list's completeness actually starts to matter.

**Correction applied to this document, not Codex's:** Codex's Phase 4
("Structured UI Renderer") lists rendering the structured schema as still
future work. That's not accurate against what's live — confirmed by reading
`ask-answer.component.html`: `reading.acknowledgment`, `.interpretation`,
`.summary_and_assurance`, `.guidance.practical_actions`, and
`.guidance.remedies` all render as distinct elements today, and the old
regex-based markdown section-parser was deleted, not kept as a fallback.
What's genuinely still missing is the *richer* version both drafts describe
elsewhere — persona-differentiated payloads (one backend response, three
different depths), `next_paths.app_links` as clickable in-app routes, and
distinct "cards" per section rather than one flowing bubble. Phase 4 above
stays tagged DONE for the basic case; the richer version is folded into
"Persona depth rendering" under "Explicitly not built," not treated as a
separate unstarted phase.

### Resolved, 2026-08-08 (second pass)

The open items above were settled in a follow-up exchange. Recording the
decisions and their concrete dependencies here so they don't need
re-litigating a third time:

- **`follow_up` is conversation metadata, not an intent.** `AskIntent` stays
  at its current 7 values. Add a separate `is_follow_up: bool` signal
  instead. Precision note: it must **not** be derived from
  `thread_domain is not None` — that conflates "thread has an established
  *domain*" with "this turn is structurally a follow-up." A thread whose
  first turn was a clarification has no established domain
  (`_thread_established_domain()`, `ask_stream_routes.py:39-51`, returns
  `None` for exactly that case by design) but its second message is still a
  follow-up. Derive `is_follow_up` from thread/message presence directly
  (e.g. `bool(thread_id and existing_messages)`), not from the domain-
  continuity check.
- **Multi-domain synthesis schema, short-term/DB-compatible:** keep
  `AskMessage.domain` as a plain string (`"synthesis"` or the primary
  domain), add `domains: string[]`, `primary_domain`, `secondary_domains`,
  and `answer_type: "single_domain" | "multi_domain_synthesis"` inside the
  `evidence` JSON bridge — no schema migration, consistent with how
  `structured_reading`/`references` are already stored there. UI badge
  becomes `ANSWER · CAREER + MARRIAGE` for the synthesis case. **Concrete
  dependency this creates:** `_thread_established_domain()` must be updated
  in the same change — if a synthesized turn ever persists a literal
  `domain: "synthesis"`, that value fails `AskOrchestrator.route()`'s
  `thread_domain in AGENT_REGISTRY` check on the next turn and silently
  breaks the thread-continuity fix shipped earlier today (a follow-up on a
  synthesized answer would fall back to fuzzy routing instead of
  continuing). Fix: when `answer_type == "multi_domain_synthesis"`, resolve
  continuity from `primary_domain`, not from `domain`.
- **Intent Router and Domain Router are separate node *contracts*, not
  necessarily separate calls yet.** Near-term: one `route()` implementation
  returns both, matching today's `RoutingResult` shape (already has
  `domain` and `intent` as distinct fields). Formalize as
  `IntentRouterNode`/`DomainRouterNode` types when Item 6 (explicit node
  contracts) is built, so `ContextPlanner(domain, intent, persona,
  thread_context)` has a clean two-input shape to depend on.
- **`admin/client.py` reconciliation:** owned by Codex's session, since she
  has live context on the file. Her reconciliation plan (diff current tree
  against `origin/main`, distinguish which changes are whose, keep already-
  deployed fixes, don't apply the stale worktree patch blindly) matches
  what was already told to the spawned task session. Not part of either
  agent's stated Ask-feature ownership — worth the user confirming the
  hand-off explicitly rather than it being assumed by default.
- **Section-level repair:** confirmed narrow scope — more precise repair
  message text only, no partial-object regeneration. No change from Item 5
  above.
- **Verifier additions, confirmed backend-only, four items:** confidence-
  vs-evidence-strength, remedy-overclaim (no net today — same gap
  dosha-overclaim had before this session), unsupported-timing-certainty,
  and required-sections-by-intent. Matches Item 2 above; no new items, just
  confirmed alignment on the same four.

**Scope named by Codex but out of scope for this document:** the "Future
Ideal" section's cross-feature integration (Ask pulling in Today, Dashas,
Yantra/transits, Remedies practice tracking, Calendar/muhurta, Charts/vargas,
Compatibility, preferences, location panchanga, and knowledge ingestion) is
real long-term product surface area, but every item on that list depends on
agents this document's roadmap hasn't reached yet. Worth keeping on record
as the eventual destination; not worth sequencing until Phase 6 above is
further along than 2 of 10 domains.

## Update 2026-08-09: Retrospective-vs-future tense gap (Codex, live user testing)

Found via actual live testing, not review-by-reading: a user on an
already-retired profile asked the career agent "when did my career
inception start and when did retirement happen?" — a retrospective,
event-history question. The agent answered it as a future prediction,
generating future windows (~2023/2049) instead of recognizing the person
is already retired and the question is about the past. Verified both
technical root causes directly before recording this, not taken on trust:

- `detect_intent()` (`astrospace/agents/intent.py`)'s `timing` pattern is
  a bare `\bwhen\b` — "when did X start" and "when will X happen" produce
  the identical `timing` intent. There is no tense distinction anywhere in
  the intent layer.
- The context bundle (`assemble_domain()`, `astrospace/context/
  assembler.py`) carries `as_of` (today's date) but no `age`, `life_stage`,
  or `retired`/`working`/`student` fact. Nothing in the bundle states the
  person's current life stage as a precomputed fact — that inference is
  left entirely to the model, which is exactly the failure mode this whole
  architecture exists to prevent ("the model does not decide what
  astrological facts exist," this document's Architecture Principle,
  reaffirmed in the 2026-08-08 Update section above). A sufficiently
  careful model could in principle derive age from birth data + `as_of`
  itself, but leaving that arithmetic to the model instead of computing it
  once, deterministically, in the backend is the same category of gap the
  registry/verifier/safety-net work all season has been closing elsewhere.

**Severity, per Codex's own framing, and independently agreed with:** this
isn't domain-specific. The same failure recurs for marriage ("when did we
meet" vs "when will I marry"), children, property, health, and any
retirement/life-event question, in any domain, present or future. It's a
Context Engine / intent-layer gap, not a career-agent bug — fixing it once
here fixes it for every domain, including ones not yet built.

**This is not a quick patch — it's the concrete specification Item 3 (the
intent-aware context planner) was missing.** Item 3 above already says
"make `assemble_domain` intent-aware" without saying precisely what that
means; this finding gives it a real, validated requirement:

1. `detect_intent()` (or a new field alongside it) needs a tense
   classification — retrospective ("when did X start/happen") vs.
   current-state vs. planning vs. future-prediction — not just a single
   `timing` bucket covering all four.
2. The context bundle needs a deterministic profile-facts block computed
   once in the backend, not inferred by the model: current age at minimum;
   life-stage flags (retired/working/student) where the profile has data
   to support them, not guessed.
3. Domain agent prompts need those facts and an explicit instruction:
   respect profile age/life-stage and question tense over generating a
   plausible-sounding future timeline when the question was never asking
   for one.
4. Candidate verifier invariant, for later once the above ships: if a
   generated timeline (a date, dasha window, or age reference in the
   answer) conflicts with the profile's known current age or the
   question's retrospective framing, that's a violation — same category as
   the citation/prohibited-verdict/dosha-overclaim checks already there.

**Sequencing:** folded into Item 3, not a new unscoped workstream — this
is what makes Item 3 buildable rather than a vague intention. Given the
severity (recurs across every domain, damages trust even when the
astrology math is internally correct) and that it was raised specifically
in the context of "discuss before scaling more domains," it moves ahead
of the confidence/remedy verifier checks in Item 2's remaining queue,
though not ahead of finishing what's already in flight (the safety-regex
fix, PR #10, stands on its own and is unaffected by this).

**Follow-up (Codex): the profile-facts block is broader than age/life-stage
alone.** Requirement 2 above should read as the minimum, not the ceiling.
Where the profile has the data, the same deterministic block should also
carry: relationship/gender context when relevant to the domain (marriage,
children), current location/country (for practical framing — timezone,
festival/observance calendar, muhurta locality), and known status facts
beyond retired/working/student where available. Stated as a principle, not
just a field list: **logical/common-sense reasoning runs before
astrological interpretation, not after** — astrology refines and
contextualizes an answer built on correct demographic reality, it does not
get asked to override that reality. This doesn't change Item 3's shape
(still a deterministic backend-computed block + tense classification +
prompt instruction + verifier invariant), it widens what "profile facts"
means inside it, and it's the reason requirement 4's verifier invariant is
framed as *reject-or-clarify* on conflict, not merely *flag*.

## Cross-Check: Qwen's 2026-08-08 Review (fresh-eyes read, doc-only)

A third review, done from this document's text alone — no codebase access.
Genuinely useful for exactly that reason: it caught two things nobody with
the code in front of them had flagged (SSE's missing error contract, the
verifier's blind spot to under-provisioned context — both folded into Items
2 and 4 above, with citations). It also, unavoidably, proposed fixes for a
system that doesn't quite match what's actually built, since it couldn't
check. Splitting the difference precisely, each checked against real code
before being accepted or declined:

**Adopted (see Items 2 and 4 above for the full write-up):** the SSE
`fatal_error` event contract, the verifier's under-provisioning blind spot
as an explicit Item 4 dependency, and re-auditing `dosha_overclaim_kind`/
`prohibited_verdict` for the paraphrase-evasion weakness `refer_out_kind`
already found and fixed in itself. Also adopted: the grounding-rules
enforcement table above, and this section's own ADR-001 framing on the
rejected tool-access decision.

**Declined — based on a mental model this system doesn't have.** Two of
the "Critical Gaps" describe problems that require a distributed,
multi-service architecture: caching across "shared backend services,"
resilience when "the chart service is unavailable," a C4 container diagram
of the Context Engine as its own deployed component. Checked directly:
`assemble_domain()` (`astrospace/context/assembler.py`) imports `swisseph`
and computes entirely in-process — there is no chart service, no network
call anywhere in `astrospace/context/`, nothing that can be "down"
independently of the FastAPI process itself. This is a monolith, per this
repo's own CLAUDE.md. A diagram of services that don't exist would
document an imagined system, not this one. If ephemeris computation is ever
a measured bottleneck, that's a caching decision to make against real
profiling data then — not a speculative diagram now.

**Declined — solving an already-shipped problem.** The review asks whether
Ask's UI is web or mobile, and suggests adding progress events because
generation might otherwise feel unresponsive. Checked: `askService.stream()`
has exactly one caller in the whole frontend — `ui/src/app/features/mobile/
ask/` — it's mobile-only by design, not an open question. And the progress
events it asks for already exist and are already live: this session
watched "Career & Profession specialist is interpreting…" render mid-stream
in a real browser earlier today. Both suggestions are reasonable in the
abstract and already true in practice; the review just couldn't see the
running app to know that.

**Declined — conflicts with a decision already made, not silently
overridden.** "Make `domain` an array now, even if always length 1" directly
contradicts the multi-domain schema settled with Codex two sections above:
`domain` stays a plain string, with `domains`/`primary_domain`/
`secondary_domains`/`answer_type` added alongside it in the `evidence`
bridge, chosen specifically to avoid a migration. Recording the conflict
here rather than picking one silently — if `domain`-as-array is ever
revisited, it should be an explicit reopening of that decision, with both
proposals on the table, not whichever document someone read most recently.

**Declined — premature for this codebase's own stated bias.** Reserving an
unused `practitioner_details` field now, "to avoid a future breaking
change," is exactly the kind of speculative schema field this repo's
conventions argue against (CLAUDE.md: "Don't design for hypothetical future
requirements"). Persona-differentiated rendering isn't scoped yet. Noted as
a deliberate non-decision, not an oversight — if it becomes real work, add
the field when there's an actual consumer for it.

**Deferred, not declined — right idea, wrong size for right now.** The
full observability ask (per-node latency histograms, Prometheus-style
counters, business-metric dashboards for `clarification_needed` vs.
`domain_not_ready` rates) is reasonable for a system with production
traffic to measure. This one has two configured domains and no evidence of
live traffic yet in anything this document tracks. Item 1 above ("log which
violation fired") is sized to what's actually needed right now; the fuller
metrics buildout is worth revisiting once Phase 6 has shipped enough
domains that "which agent do we add next" is actually a traffic-driven
question rather than a guess either way.

## Update 2026-08-10: the consultation validation loop (wealth first)

What shipped on `claude/wealth-validation-loop-w0g7os`, and — more usefully —
the two decisions inside it that are easy to get wrong on a second pass.

### The problem this solves

Every reading this app produces is unmeasured. Nobody knows whether they are
any good, because nothing has ever been committed to in advance and checked
afterwards. Real astrologers open by validating — asking about the past — and
only then answer. Copying that naively produces a **cold-reading machine**:
ask "have you had money trouble?", hear yes, reply "your chart shows that".
Nothing was tested, and the reader was handed their own disclosure back as
insight. That is not a hypothetical failure mode; it is the actual
professional technique, and it is where a straightforward implementation
lands by default.

### Decision 1 — order, enforced structurally

The agent commits to a falsifiable claim, with a confidence, **before** the
question reaches the reader. Everything else follows from that:

- `ValidationProbe` (`db/models.py`, migration `20260810120000`) writes
  `claim_text`, `claim_candidate`, `confidence` and `committed_at` NOT NULL at
  insert; `answer_key`/`answered_at` can only be filled in later, and the DB
  has a CHECK tying answered-ness to a scored status.
- `crud_mobile.record_validation_answer()` takes no claim parameters at all —
  there is no code path that can revise a prediction after seeing its answer.
  That is what makes the stored hit rate an honest number rather than a
  self-graded one.
- The `validation_needed` envelope carries the question and the options and
  **not** the committed claim. Showing a reader what the chart expects tells
  them what to say. The claim is revealed by the answer endpoint's response,
  after they have committed — which is also the moment it becomes worth
  something to them.
- The persisted thread turn stores the question, never the claim: thread
  history is replayed to the model on later turns, and a claim visible there
  would let a future reading launder its own prediction as evidence.

### Decision 2 — the engine picks the slots, the model writes the words

`context/validation.py` decides *where* this chart is genuinely ambiguous;
`agents/validation_agent.py` only writes the question and the option copy. If
the model picked slots too it would ask about things the chart cannot speak
to, and every answer would be unfalsifiable.

"Genuinely ambiguous" is defined concretely, not by vibe: a planet gives the
results of the houses it **rules** and of the house it **occupies**, so when
those point at different areas of a reader's financial life, both readings are
classically defensible and only the reader knows which happened. Slots that
resolve to one reading are not emitted at all.

Fatigue is treated as a real risk, not a footnote: one question per turn, at
most two slots ever considered, asked once per chart (a unique index, not a
caller's good intentions), always skippable, and every slot carries a
`neither` option — without it the reader is forced into one of the chart's own
guesses and the hit rate is inflated by construction.

### Also landed

- **`timeline`** (`context/timeline.py`, new bundle section) — the four
  overlapping dated windows previously spread across `retrospect`,
  `dasha_relevance` and `gochara`, flattened into one sorted list with an age
  at every boundary, a past/current/upcoming `status`, a `domain_relevant`
  flag, and `next_transition`. Base-prompt rule 12.
- **`life_context`** (new bundle section) — answered probes plus a running
  `calibration` hit rate, fed back into every reading. Base-prompt rule 13
  carries the anti-cold-reading rule in as many words: never hand a reported
  fact back as a discovery.
- **The third-party death gap in `safety.py` is closed** — see the checklist's
  §C. It was closed *first*, deliberately: once bundles carry reader-reported
  life events, the model has a reason to write about a family member's
  lifespan that it did not have before.

### What is deliberately not done

Wealth only, and the asking half is behind `AskRequest.validate_first`
(default `False`) until a client can render the envelope. Birth-time
rectification — the real prize, and the reason the data is worth storing — is
a later pass. All three are recorded with unblock conditions in the
checklist's Deferred backlog rather than here.

### Failure posture

Every step of the loop fails open. No slots, a model call that raises, a draft
that fails `probe_violations`, a probe store that errors — all fall through to
the ordinary reading path. The probe is a bonus; the answer is the product.

### Update 2026-08-11: PR #20 review round

Independent adversarial review of the loop. **The commit-before-ask invariant
held under direct attack** — a planted canary claim reached neither the SSE
envelope, nor the persisted `AskMessage.evidence`, nor `life_context_section()`,
and `_history_from_thread` replays only `{role, content}`, so a claim cannot
reach a later model turn. Nothing in the design changed. Everything below was
surrounding code.

Three findings are worth keeping, because each is a *class* of mistake rather
than a one-off:

**A combined guard clause silently merged two different concerns.**
`if key in seen or slot_id in exclude: continue` skipped `seen.add()` for
excluded slots, so answering a question removed the dedup barrier it was
providing and its suppressed twin surfaced next turn — the reader asked the
same thing twice in different words, which is exactly what "asked once"
exists to prevent. Dedup is a property of the slot set; exclusion is a
property of one reader's history. Resolve the first, then apply the second.

**Fail-open is a claim about the whole request, not about one try/except.**
`check_validation` caught its exceptions and returned None as designed, but a
rejected probe insert left the request's SQLAlchemy session in a failed
transaction — and the next query is the one assembling the reading. The reader
got `fatal_error` instead of their answer, from a feature documented as a
bonus. Session hygiene now lives in the DB layer, which is the only layer that
knows a transaction was in flight.

**A safety pattern's false positives are as expensive as its misses.** The
lifespan patterns matched `live (?:until|to|for|past|beyond)` and stopped
there, which swallows "live to *see*", "live to *enjoy*", and "live beyond
one's *means*". A match REPLACES the whole answer with the longevity
refer-out, so each false positive cost a reader their reading and told them
the app would not discuss their lifespan — about a question they never asked.
The rewritten patterns key on the *object* ("live to 80", "live to a ripe old
age"), which is what actually makes the verb a lifespan claim.

**On why the tests did not catch it.** The negative test for those patterns
contained exactly one "live" sentence — "will live comfortably", the adverb
case the anchor was designed for — so the failing construction was never
tested. The same blind spot was encoded in the test as in the code, which is
how a green suite coexisted with three live false positives. The fix was to
write the adversarial set from the *app's* vocabulary rather than from
paraphrases of the positive cases: what does this product legitimately say
that happens to contain "live", "survive", or a duration? Periods ending,
money advice, foreign residence, businesses and partnerships. That set
immediately found four more problems than the review had listed, including a
**pre-existing** false positive in shipped `main` — `you have ... years left`
was an absolute pattern, so "you have 2 years left in this Saturn dasha" read
as a death verdict. Every fix in this round was also verified by reverting it
and confirming the new test goes red.

**On the intermittent test.** `test_an_already_asked_slot_is_not_asked_again`
failed for two reviewers and passed three times for the author. Neither run
was wrong. It was the one test in its file that did not stub the model call:
without provider credentials `run_probe` raised, `check_validation`'s
fail-open swallowed it, and the assertion passed for a reason unrelated to
what it claimed to check; with credentials it ran for real and the assertion
broke. The three test counts reconcile the same way — 1617 was the true total,
1616 was a stale figure transcribed into the ledger from a run before the last
test was added, and the reviewer's "1616 passed + 1 failed" is that same 1617
with the flaky one red. The file now carries an autouse fixture that fails any
test reaching the provider layer, so the failure class is un-writable here
rather than merely fixed.

## Update 2026-08-17: Ask latency and CE payload growth — the shape, not the parameters

Two symptoms reported from live use: prediction generation after a prompt
sometimes exceeds a minute, and the CE payload gets bulkier day by day. They
were profiled against real code rather than reasoned about, and they turn out
to be two faces of one property this document already named — **the bundle is
assembled whole, before the model has reasoned about the question** — plus one
consequence of that property this document has not previously recorded.

The useful correction here is about *level*. The first pass at this produced a
list of parameter fixes: drop `indent=2`, lower `kb_limit`, add prompt caching,
cap `max_tokens`. Every one of those is real and some are worth an hour. None
of them changes the shape, and the shape is what is generating both symptoms on
a schedule. `kb_limit` has already been retuned twice (12 → 30 → 50); a third
retune is the same move a third time.

### What was measured

Profiled against a real chart (1985-06-14, Chennai) on a clean checkout:

```
chart build                          0.002s
assemble_domain(wealth)              0.349s   ← 0.31s of it the gochara boundary walk
assemble_domain(wealth, no gochara)  0.043s
```

Bundle sizes, serialized as the prompt actually serializes them
(`json.dumps(bundle, indent=2)` at `domain_agent.py:380`):

| domain | full | references + passages | **structural floor** | floor as % |
|---|---|---|---|---|
| career | 59,186 B | 8,687 B | **49,955 B** | 84% |
| wealth | 72,355 B | 23,715 B | **47,022 B** | 65% |
| marriage | 54,030 B | 10,249 B | **43,151 B** | 80% |
| health | 61,950 B | 16,481 B | **44,499 B** | 72% |

Roughly 13k–18k tokens by byte estimate, and JSON tokenizes denser than prose
so the real figure is higher. Two limits on these numbers, stated so nobody
treats them as a ceiling: the profiling container had no database, so
`source_passages` returned `[]` through `assembler.py:651`'s `except Exception`
— production bundles carry up to 8 more book chunks on top of every row above;
and one chart with one set of active transits is a floor for the gochara walk,
not a worst case.

### The finding that reframes the payload problem

**The structural floor is 65–84% of the bundle and it is 100% unconditional.**
`assemble_domain()` has no intent-awareness at all: `houses`, `karakas`,
`vargas`, `retrospect`, `timeline`, `jaimini_karaka_array`, `gochara`,
`dasha_relevance` and every per-planet enrichment compute identically whether
the question is "when will I get a promotion?" or "should I start my own
business?". The *only* thing that narrows is `references`/`source_passages`,
via `subdomain_match`.

And that narrowing already works. A career question that matches a subdomain
confidently drops from 15 references to 3–4 — and the bundle still sits at
~52,000 B, against ~59,000 B unmatched. Perfect reference retrieval saves ~12%.

So `kb_limit` is a lever on 16–35% of the payload, and it is the only lever
anyone currently has. That is the whole reason it has been retuned twice: it is
the one number in reach, so it absorbs pressure that belongs elsewhere. Setting
it to zero still leaves ~47,000 B.

**The pressure is live, not historical — and it is now measured, in one day.**
The table above was taken on a checkout that predated `#71` (Sharma BPHS
cross-check of the career 10th house) and `#73` (Brihat Jataka Ch. X
extraction). Both are now in `main`, and they took career from 15 references to
29. Re-measuring the same chart, same question, against `main` after them:

| domain | before (this session) | after `#71`+`#73` | delta |
|---|---|---|---|
| **career** | 59,186 B | **69,608 B** | **+10,422 B (+17.6%)** |
| wealth | 72,355 B | 72,354 B | — |
| marriage | 54,030 B | 54,016 B | — |
| health | 61,950 B | 61,961 B | — |

Career's `references` block alone went 8,687 B → 18,618 B. **One KB extraction
pass, one day, +17.6% on every career Ask.** That is the reported symptom
reproduced as a number rather than an impression, and it is the strongest single
argument for Item 4: the KB corpus work is nowhere near done, so this recurs on
every extraction pass, and `kb_limit` is the only thing currently standing
between it and the prompt.

Note what the other three rows show: they did not move. Growth is per-domain and
arrives in steps, which is exactly why it reads as "bulkier day by day" rather
than as a single regression anyone would have caught.

### Where the latency actually is

Not in the engine. Assembly is ~0.35s against a wall clock exceeding 60s.
Almost all of it is **one non-streamed model call**: `base.py:75`
`_run_structured_anthropic` uses blocking `messages.create` with `tool_choice`
forcing a single `deliver_reading` call at `max_tokens=8192`. Nothing reaches
the reader until the whole tool-call JSON closes; `orchestrator.run()` emits two
static status frames and then the SSE stream is silent.

Three things compound, in order of size:

1. **The cap removal.** `ed30589` (2026-08-10) dropped the ~350-word soft cap
   "in favor of completeness" and raised `max_tokens` 4096 → 8192 in the same
   change. On a blocking call, latency is essentially `output_tokens /
   throughput` — that change removed the only bound on the numerator. It is why
   this got worse over time instead of being bad from the start. The product
   reasoning behind it was right; the latency consequence was simply not part of
   the decision.
2. **The repair round trip.** `_agent_run_and_verify` retries once on any
   violation and resends the entire prompt. A verification miss does not add a
   margin, it roughly doubles wall clock. That is the "*sometimes* over a
   minute".
3. **No prompt caching, and a cache-buster that would defeat it anyway.**
   `grep cache_control` over `astrospace/` returns nothing. Separately,
   `_profile_facts` stamps `as_of` at microsecond precision and it propagates
   into `gochara.as_of` and every timeline entry, so no two requests share a
   prefix even if caching were added tomorrow.

Minor but real: `source_retriever.py:71` opens a fresh `psycopg.connect` per
Ask with no pool, and the ledger projection, stored probes and passage
retrieval all run serially.

### Item 4 is now the top of the sequence — the Context Planner (Part A)

This document's revised near-term sequence, Item 4, says it plainly: *"Make
`assemble_domain` intent-aware — this **is** the Context Planner from Phase
3/the graph above, not a new component."* The graph in "Revised Implementation
Bias" lists "Context planning" as step 4 of the boring graph. Phase 3 is marked
"DONE for career + marriage; **not intent-aware**".

It was never built, and the measurement above is what it costs. `detect_intent()`
already runs, already threads through `PreparedRun.intent`, and is used only to
*label the response* — never to shape what is assembled.

Nothing about that analysis is new; what is new is that it should now be read as
the top of the sequence rather than the fourth item on it, because the payload
symptom is the one actively degrading and it is the only item that addresses the
structural 65–84%.

The dependency this document already recorded under Item 4 stands and is the
part most likely to be skipped: today the bundle is always full, so `verify()`
only has to catch **over**-claiming — a citation to something absent. The moment
the bundle is trimmed per intent, **under**-provisioning becomes possible and no
check in this system can see it. Trimming and a bundle-completeness assertion
ship together, or grounding regresses with a green suite.

**Ownership: taken by the human maintainer, 2026-08-17. Shipped 2026-08-18
(PR #76).** Scoped as a function-signature change across
`astrospace/agents/*` and `astrospace/context/assembler.py`, no schema and
no migration — see the sequencing table below for what actually landed.

### Part B: layer the bundle by what actually varies — NOT STARTED, blocked pending its own PR

New to this document. The natal half of the bundle is recomputed from Swiss
Ephemeris on every single Ask, and it is immutable: `houses`, `karakas`,
`vargas`, `yogas`, `doshas`, `jaimini`, `nakshatra_detail`, `d60_*`,
`vimshopaka_bala`, `shayanadi` never change for a given kundli. Only gochara,
dasha position, `timeline` and `retrospect` depend on `as_of`, and those move at
*daily* granularity, not per-request.

Three layers instead of one:

- **`natal_core`** — computed once at kundli creation, persisted, versioned by
  engine version. The invalidation discipline already exists in this repo:
  catalog tables are seeded from the engines, never hand-authored.
- **`temporal_layer`** — computed once per `(kundli_id, date)`.
- **`question_layer`** — the only part assembled per request: references,
  subdomain match, profile ledger, life context.

The payoffs compound rather than add. It removes the gochara walk from the
request path. It makes the prompt prefix byte-identical for 24 hours across
every question a reader asks, which is the precondition that makes prompt
caching hit at all. It yields a real cache key, `(kundli_id, engine_version,
date, domain, intent)`.

And it gives the payload problem somewhere to live. A materialized bundle is a
schema with a migration, so adding a field becomes a reviewable act instead of
one more key in a dict literal — which is the actual mechanism by which this
grew day by day.

**Compatibility with ADR-001, stated up front because the shape invites the
wrong reading:** this is not a tool layer and it does not move any decision to
the model. It is orchestrator-side deterministic assembly with a cache in front
of it — precisely what ADR-001 says a tool layer should be *if* one is ever
built ("tools the *orchestrator* calls deterministically to assemble a bundle
— never tools the model selects and invokes itself"). The bundle stays fixed and
known in advance before generation; `verify()`'s contract is untouched.

**Status: deliberately not started.** This is migration-shaped, which under Rule
5 means its own PR with dedicated backend and security review, not something
bundled into Part A. Sequenced as a standalone follow-up once A has landed.

### Part C: decompose generation — blocked behind B

`StructuredReading`'s five beats have different dependencies, different token
volume, and different risk, but are welded into one serial `max_tokens=8192`
generation, so wall clock is their sum. `acknowledgment` depends on the question
alone. `technical_basis` is mechanical extraction over a deterministic bundle
and carries the bulk of the output tokens — Rule 3 obliges it to be exhaustive.
`interpretation` is the judgment. `guidance` follows interpretation.

Architecturally that is a fan-out: run evidence extraction and interpretation
concurrently against the same frozen bundle, converge on a short synthesis pass,
and wall clock becomes `max(branches) + synthesis` with a small `max_tokens` per
branch.

Three caveats, all load-bearing:

1. **This is not the bad diamond this document already warned about.** "Asking
   Dasha Agent, Transit Agent, Yoga Agent, and Career Agent separately and
   synthesizing prose" fragments the *judgment*, and that warning stands. Here
   the judgment stays in exactly one place and only the mechanical extraction
   forks off the critical path.
2. **Consistency between `technical_basis` and `interpretation` is currently
   free** because one pass writes both. Fan out and it has to be enforced —
   `verify_coverage` grows. That is a real cost, not a footnote.
3. **If extraction moves to a cheaper model for tiering, the deterministic
   verifier must be re-validated against that model's own failure modes**, not
   assumed to generalize from Opus's. The verifier's regex and source-resolution
   checks were tuned against what one model gets wrong; a different model gets
   different things wrong, and this file has already recorded once what it costs
   when a test encodes the same blind spot as the code.

Depends on B's frozen, materialized bundle to fan out safely, so it is last
regardless.

### Part D: build the tool schema per request — SOURCE ENUM SHIPPED 2026-08-18; field-level repair still open

`TechnicalBasisItem.source` is a free-form string validated after the fact, and
an invalid citation costs a full second generation through the repair path. The
valid set is knowable before generation: reference ids, `source_passages` ids,
the bundle's own section names, and `profile_fact:` refs. Emitting it as a JSON
Schema `enum` in the per-request tool definition makes the most enumerable
violation class structurally impossible instead of merely detectable.

This leans on the same load-bearing property ADR-001 protects — the bundle being
fixed and known in advance is exactly what makes the enum computable — so it
reinforces that decision rather than eroding it. It is a constraint on decoding,
not a checker, so it does not touch the "the checker must not be the same
generation context grading itself" principle; the deterministic verifier stays
exactly as it is, behind it.

**Shipped 2026-08-18.** `schema.reading_tool_schema()` compiles the allowed set
into the tool's `source` enum, and `DomainReadingAgent.run_structured_reading()`
passes it per request through `BaseAstroAgent.run_structured(input_schema=...)`
(both providers). The one design decision worth keeping on record: the enum is
built from `verifier.valid_sources()` — the same function `verify()` checks
against, made public rather than reimplemented. **Never fork a second copy of
that logic for the schema.** A constraint that disagrees with its own checker
fails silently in whichever direction is looser, which is strictly worse than no
constraint; `tests/test_domain_agent.py::TestSourceEnumMatchesTheVerifier::test_enum_and_verifier_cannot_drift`
exists to fail if anyone re-derives it.

`verify()` is unchanged and still checks `source` membership. A provider that
ignores the enum, or a future provider without enum support, degrades to exactly
the previous behaviour rather than to an unchecked one — validation stays on the
general Pydantic model, so an off-enum value still parses and is caught by the
verifier instead of crashing the parse.

Honest accounting, since this document is otherwise about shrinking the payload:
the enum restates reference ids already present in the bundle, so it **adds**
input tokens — measured at +1,188 B (career), +1,836 B (wealth), +780 B
(marriage), i.e. 1.4-2.5% of the bundle. That is a deliberate trade against a
repair round trip costing an entire second reading. It is a latency win, not a
payload win, and should not be counted as one.

**Still open (D2):** where repair is genuinely needed, repair the failing
field rather than the whole object. A tense violation in `interpretation`
should not regenerate `technical_basis`. Deliberately not done in the same
change as D's enum — it touches `AskOrchestrator._agent_run_and_verify()`,
which A was concurrently editing at the time; A has since shipped (PR #76,
2026-08-18), so D2 is no longer collision-blocked, just not yet started.

### ADR-001 reaffirmed, with a second independent reason

Model-selected tools (`get_varga_chart` on demand, pull references as needed)
look like the obvious architectural answer to payload growth, and this is the
third time the idea has surfaced in this file's history. ADR-001 rejected it on
grounding: the verifier depends on the bundle being fixed and known before
generation.

The profiling adds a second, independent reason. Every model-selected pull is a
round trip, and round trips are the thing already producing the latency
complaint. The Context Planner delivers question-scoped context with **zero**
extra round trips. Phase 2 stays deferred; the reasoning is now over-determined.

### Also: the thread window contradicts this document's own Memory section

The Memory section says follow-ups "should use a compact thread summary and the
prior structured answers, not an ever-growing free-text context window."
`MAX_HISTORY = 12` raw turns at up to 8,000 chars each is up to ~96 KB of
free-text stacked on top of the bundle in a long thread — the exact thing that
section rules out. Not the cause of either symptom, but it is on the same input
budget and it is already decided.

### Sequencing and ownership

| part | what | status | owner |
|---|---|---|---|
| A | Context Planner / intent-aware `assemble_domain` | **shipped 2026-08-18** (PR #76) | Claude |
| D | per-request `source` enum | **shipped 2026-08-18** | Claude |
| D2 | field-level repair (not whole-object) | open — no longer blocked, A has landed | unassigned |
| B | `natal_core` / `temporal_layer` / `question_layer` | **blocked** — needs its own reviewed PR (Rule 5, migration-shaped); draft schema recorded, not applied | unassigned |
| C | decompose generation, fan out extraction | **blocked** behind B | unassigned |

**A, first increment, shipped 2026-08-18 (PR #76):** `assemble_domain(...,
intent=...)` trims `_planet_brief`'s decorative texture (nakshatra deity/
symbol detail, D-60 sign+deity, dhatu/rasa, varna) for `timing`/
`daily_guidance`/`comparison` intents — ~20% off a career bundle's
serialized size in the measured case. Deliberately conservative relative
to the structural-floor number above: **no top-level section is dropped by
intent in this pass** — only per-planet detail inside `houses`/`karakas`/
`jaimini_karakas` shrinks, which is why this closes Item 4 but does not by
itself close the 65–84% structural-floor gap this section measured. A
bundle-completeness assertion (`_assert_bundle_completeness()` in
`assembler.py`) ships in the same change, per the dependency this section
already named — every section name `TechnicalBasisItem.source` can cite
stays present regardless of intent, so under-provisioning stays
impossible rather than merely unlikely. Wired end-to-end: `RoutingResult.
intent` → `AskOrchestrator.assemble_context()` → `assemble_domain()`,
confirmed by orchestrator-level tests, not just an assembler unit test.
Section-level dropping (`timeline`/`gochara`/`retrospect` per intent, the
rest of the 65–84% floor) is a real, larger follow-up — not bundled with
this pass.

The parameter-level fixes from the first pass — compact JSON instead of
`indent=2` (−26% with no information loss), deduplicating repeated planet briefs
across `houses` (−13%; the test chart emitted 11 briefs for 7 distinct planets),
quantizing `as_of` to the day — are worth doing, but they belong inside A and B
as cleanup. They are not a strategy, and recording them as one is how this
problem returns in a month with `kb_limit` at 80.
