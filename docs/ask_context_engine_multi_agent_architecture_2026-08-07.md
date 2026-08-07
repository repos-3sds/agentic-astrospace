# Siddha Ask + Context Engine Multi-Agent Architecture Plan

Date: 2026-08-07

Status: planning / architecture. Do not treat this as implemented behavior.

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

### Phase 0: Stop Unsafe Generalization

Acceptance criteria:
- Unsupported domain does not fall back to generic answer.
- Unknown routing does not default to career.
- Ask returns structured `domain_not_ready` or `clarification_needed`.
- UI renders those states cleanly.

### Phase 1: Agent Skeleton Registry

Acceptance criteria:
- Agent registry exists with every planned agent.
- Each agent has explicit contract metadata.
- Enabled/disabled is explicit.
- Router checks registry before dispatch.
- Tests prove disabled agents cannot answer.

### Phase 2: Tool Layer

Acceptance criteria:
- Each required tool has a stable interface.
- Tools return structured data and errors.
- Tools include provenance where relevant.
- Agents receive tool outputs through CE bundle, not arbitrary raw DB dumps.

### Phase 3: CE Bundle Contracts

Acceptance criteria:
- Domain-specific bundle schema exists.
- Career bundle is implemented first.
- Missing-context behavior is explicit.
- Evidence refs are stable IDs that UI can display.

### Phase 4: Structured Response Renderer

Acceptance criteria:
- Frontend renders structured answer sections.
- No regex parsing of LLM markdown for core layout.
- Ask History stores and reopens structured answers.
- Follow-ups preserve thread continuity.

### Phase 5: Career Agent Production Readiness

Acceptance criteria:
- Career agent uses D1 + D10 + dasha + gochara + KB.
- Answers pass schema validation.
- Claims are grounded to CE refs.
- Safety verifier runs after generation.
- Persona variants render correctly.

### Phase 6: Add Agents by Traffic

Recommended order:

1. Career & Work
2. Daily Guidance
3. Dasha
4. Transit / Gochara
5. Relationship & Marriage
6. Remedies
7. Muhurta
8. Chart Explanation
9. Compatibility
10. Advanced practitioner modules

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

### P0

- Remove generic fallback for unsupported routed domains in mobile Ask streaming.
- Remove `career` as default domain for unknown questions.
- Add structured unsupported-domain and clarification responses.

### P1

- Create Agent Registry with enabled/disabled status.
- Define agent contracts for all planned agents.
- Define structured response schema and validator.
- Persist structured response payload in Ask messages.

### P2

- Implement Ask Orchestrator service.
- Implement Career CE bundle contract.
- Implement Career Agent with verifier.
- Update frontend renderer for structured answer cards.

### P3

- Add streaming status events.
- Add context-used chips.
- Add practitioner provenance panel.
- Add UI affordance to choose/refine context for follow-up.

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
