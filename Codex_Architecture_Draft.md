# Siddha Ask Agentic Architecture Draft

Date: 2026-08-08  
Status: Draft architecture / implementation direction  
Scope: Siddha Ask, Context Engine, domain agents, backend orchestration, structured response UI

## Executive Vision

Siddha Ask should not become a generic astrology chatbot. It should become a Context Engine-led consultation system: a disciplined guidance graph where deterministic astrology computation, curated knowledge, domain-specific interpretation, safety policy, and user persona are coordinated into one trustworthy answer.

The central principle is:

> The Context Engine computes. The agent interprets. The verifier protects trust. The UI makes the guidance humane.

This is the difference between a model that "talks astrology" and a product that can become a way-of-life guide.

## Product Philosophy

Siddha is not only an astrology app. The long-term vision is a life guidance system rooted in Vedic intelligence, daily rhythm, self-awareness, and practical next steps. Astrology is the engine, but the user experience should feel like a thoughtful consultation:

- understand the real intent behind the question
- gather the right chart and time context
- explain the technical basis without overwhelming the user
- translate it into normal, empathetic language
- summarize without fatalism
- guide the user toward next actions, questions, remedies, calendar moments, or deeper chart views

Siddha should be precise enough for practitioners, gentle enough for guided users, and trustworthy enough that it never invents certainty.

## Where We Are Now

The latest backend has a strong first skeleton for Ask v2.

Current live shape:

```text
Safety
  -> Routing
  -> Registry Gate
  -> Context Assembly
  -> Domain Agent
  -> Deterministic Verifier
  -> Repair Once
  -> Persistence
  -> Structured Stream Response
```

What is already established:

- Ask v2 has a real `AskOrchestrator`.
- Career and Marriage are configured domain agents.
- Unsupported domains return `domain_not_ready` instead of silently falling back.
- Ambiguous routing can return `clarification_needed`.
- The model is forced into a structured `StructuredReading` contract.
- The Context Engine assembles the bundle before the model sees it.
- The domain agent explains the bundle; it does not recalculate chart facts.
- The verifier checks citation validity, routed-domain consistency, prohibited verdicts, and dosha fatalism.
- There is exactly one repair attempt after verification failure.
- Failed generation or failed verification does not create a new successful answer.

What is not yet ideal:

- The graph is graph-shaped in discipline, but not yet graph-shaped in runtime.
- The orchestrator is one sequential Python class, not explicit node execution.
- Context planning is still broad and mostly domain-driven.
- Verification is not yet intent-specific enough.
- Multi-domain questions are currently treated mostly as ambiguity.
- Ask UI still needs to fully honor the structured response shape.
- Only Career and Marriage are enabled as real domain specialists.
- There is no mature agent contract registry for every future domain.

## Architecture Principle

The model must not decide what astrological facts exist.

The backend should decide:

- what domain the question belongs to
- what intent the user has
- what chart layers are relevant
- what dasha, transit, yoga, dosha, strength, and reference context is allowed
- what evidence can be cited
- whether the answer is safe and grounded

The agent should decide:

- how to explain the approved evidence
- how to phrase uncertainty
- how to translate technical context into life guidance
- what follow-up paths are useful

This separation is load-bearing. It protects Siddha from becoming a confident but ungrounded chatbot.

## Target Architecture

```text
User Question
  -> Safety Node
  -> Intent Router
  -> Domain Router
  -> Registry Gate
  -> Context Planner
  -> Context Engine Bundle Builder
  -> Domain Specialist Agent
  -> Deterministic Verifier
  -> Section Repair Loop
  -> Persistence + Thread Memory
  -> Structured Streaming Response
  -> Persona-Aware UI Renderer
```

## Core Nodes

### 1. Safety Node

Purpose:

- classify excluded or sensitive requests before any chart interpretation
- prevent death/lifespan predictions
- prevent medical diagnosis
- prevent directive legal, financial, or destructive advice
- prevent fatalistic dosha language
- prevent manipulative remedy claims

Why this decision:

Safety must be a gate, not a prompt suggestion. A model should not be allowed to "try its best" on prohibited questions.

Output examples:

- `allowed`
- `refer_out`
- `needs_professional_context`
- `blocked_verdict_type`

### 2. Intent Router

Purpose:

Detect what the user is asking for.

Primary intents:

- `timing`
- `suitability`
- `explanation`
- `comparison`
- `remedy`
- `daily_guidance`
- `follow_up`
- `general_guidance`

Why this decision:

Domain alone is not enough. "Will I get married this year?" and "What does Venus in D9 mean?" are both Marriage, but they require different evidence and response shape.

### 3. Domain Router

Purpose:

Map the question to life domains.

Domains:

- Career
- Marriage
- Wealth
- Children
- Health
- Education
- Foreign / relocation
- Family property
- Spirituality
- Litigation

Why this decision:

Top-level agents should be life-domain agents, not technique agents. Dasha, Transit, Vargas, Remedies, and Muhurta are evidence providers or product modules, not primary conversational identities.

### 4. Registry Gate

Purpose:

Allow only configured, verified domain specialists to answer.

If a domain is not ready, return:

```json
{
  "type": "domain_not_ready",
  "domain": "wealth",
  "available": ["career", "marriage"]
}
```

Why this decision:

This is the trust boundary. Siddha should never pretend that a specialist exists when it does not.

### 5. Context Planner

Purpose:

Choose the required Context Engine sections for the routed domain and intent.

This should be deterministic/config-first.

Example: Career + Timing

```text
D1
D10
10th house/lord
6th, 2nd, 11th supporting houses
Vimshottari dasha stack
Relevant gochara
Career references
Convention notes
```

Example: Marriage + Timing

```text
D1
D9
7th house/lord
Venus, Jupiter, Mars
2nd, 4th, 8th, 12th supporting houses
Dasha relevance
Gochara
Marriage references
Dosha flags with caution rules
```

Why this decision:

The planner can reduce latency and improve relevance, but it must not hand context selection to the model. If an LLM planner is introduced later, its output must be schema-validated and must fall back to the full deterministic bundle on failure.

### 6. Context Engine Bundle Builder

Purpose:

Build the approved evidence packet.

Bundle sections:

- profile facts
- chart convention
- D1 placements
- relevant vargas
- houses and lords
- karakas
- dasha stack
- transit context
- yogas and doshas
- strengths
- curated references
- source passages
- limitations and convention flags

Why this decision:

Every answer should be auditable. The bundle is the contract between deterministic astrology and model interpretation.

### 7. Domain Specialist Agent

Purpose:

Interpret the approved bundle using a structured response format.

The agent must not:

- recalculate chart facts
- invent placements
- invent citations
- browse the KB directly
- call free-form tools
- answer outside its routed domain

The answer follows Siddha's 5-beat consultation pattern:

1. Acknowledge intent
2. Cite gathered context
3. Interpret technically
4. Explain in normal language
5. Summarize and guide next paths

Why this decision:

This keeps the experience warm and intelligent while preserving grounding.

### 8. Deterministic Verifier

Purpose:

Check the generated structured answer before persistence.

Verifier responsibilities:

- all cited sources resolve to bundle references or valid bundle sections
- routed domain matches bundle domain
- required response sections are present
- no prohibited verdicts
- no fatalistic dosha language
- no unsupported timing certainty
- remedies are not framed as paid removal
- confidence language matches evidence quality

Why this decision:

The verifier is Siddha's immune system. It should remain deterministic as long as possible. A second LLM verifier should be considered only after deterministic checks are exhausted.

### 9. Repair Loop

Current loop:

```text
Agent answer
  -> Verify
  -> If failed, repair once
  -> Verify again
  -> Pass or fail honestly
```

Future loop:

```text
Agent answer
  -> Section-level verification
  -> Repair only invalid sections
  -> Verify again
  -> Persist or return grounded failure
```

Why this decision:

Loops should increase trust, not create unpredictable behavior. Open-ended agent loops are not appropriate for the current product stage.

### 10. Persistence + Thread Memory

Purpose:

Persist only final, verified outcomes.

Thread memory should store:

- user question
- assistant structured answer
- routed domain
- intent
- context references
- schema version
- safety classification
- follow-up continuity metadata

Why this decision:

Follow-ups must continue the same domain context without resending old questions as new threads or regenerating old answers.

### 11. Structured Streaming Response

Purpose:

Expose the graph's progress to the frontend.

Recommended events:

```json
{ "type": "status", "stage": "understanding_intent", "label": "Understanding your question..." }
{ "type": "status", "stage": "routing", "label": "Routing to the right specialist..." }
{ "type": "status", "stage": "gathering_context", "label": "Gathering your D10, dasha, and transits..." }
{ "type": "status", "stage": "interpreting", "label": "Career specialist is interpreting..." }
{ "type": "done", "status": "answered", "reading": {} }
```

Why this decision:

Users should see Siddha thinking through a trustworthy process, not staring at a mysterious spinner.

## Why Not Free-Form Tool-Calling Agents Yet

We should not give domain agents direct adaptive access to tools like:

- `get_varga_chart`
- `get_dasha_window`
- `retrieve_kb_passages`
- `get_transit_context`

at this stage.

Reason:

The previous free-form tool path created the exact trust problem we are fixing: answers could look confident while being under-grounded or routed incorrectly.

The better near-term design is:

```text
Deterministic Context Planner
  -> Approved CE Bundle
  -> Agent Interpretation
  -> Deterministic Verification
```

not:

```text
Agent decides what tools to call
  -> Agent decides what context matters
  -> Agent answers
```

Future tool access can exist, but only as orchestrator-owned deterministic tools or tightly scoped planner tools with validation.

## Multi-Domain Synthesis

Future state:

If the user asks:

> Will my job change affect marriage?

The system should not force clarification if both domains are explicitly present. It should run a synthesis path.

Target shape:

```text
Question
  -> Router detects multi-domain intent
  -> Registry checks Career and Marriage
  -> Career context bundle
  -> Marriage context bundle
  -> Synthesis node
  -> Verifier
  -> Answer
```

Important distinction:

- Ambiguous: "Is this good?" -> clarify
- Multi-domain: "career and marriage" -> synthesize if both domains are ready

Why this decision:

Real consultations often span domains. But synthesis should come after planner and verifier maturity, not before.

## Agent Contract Template

Every future domain agent should have a contract.

```yaml
agent_id: career
display_name: Career Specialist
enabled: true
owned_domains:
  - career
allowed_intents:
  - timing
  - suitability
  - explanation
  - comparison
required_context_by_intent:
  timing:
    - D1
    - D10
    - dasha_relevance
    - gochara
    - references
disallowed_outputs:
  - guaranteed job change
  - directive financial advice
  - unsupported timing certainty
persona_depth:
  guided: plain, short, low technical density
  balanced: standard explanation with limited technical basis
  practitioner: full technical basis and references
fallback_behavior: domain_not_ready
```

## UI Rendering Vision

The UI should render structured answers as consultation cards, not raw markdown.

Recommended sections:

- intent acknowledgment
- context gathered
- core guidance headline
- technical basis cards
- what this means for you
- confidence and caveat
- next paths
- related app routes
- follow-up questions

Persona behavior:

- Guided: hide deep technical detail by default
- Balanced: show summary + expandable technical basis
- Practitioner: show full technical basis, references, and chart links

Why this decision:

The same backend answer should feel appropriate to different users without changing the truth underneath it.

## Roadmap To Ideal Architecture

### Phase 0: Freeze Principles

Document the non-negotiables:

- no silent fallback
- model interprets, CE computes
- deterministic verifier before persistence
- unsupported domains are honest
- dosha is a flag, not a verdict
- remedies are traditional supports, not paid removal

### Phase 1: Make Nodes Explicit

Refactor the orchestrator into explicit node contracts while keeping sequential runtime.

Target nodes:

- SafetyNode
- IntentRouterNode
- DomainRouterNode
- RegistryGateNode
- ContextPlannerNode
- ContextAssemblyNode
- AgentRunNode
- VerifierNode
- PersistenceNode

Acceptance criteria:

- each node has typed input/output
- each node is independently testable
- route handler remains thin
- no behavior regression

### Phase 2: Strengthen Verification

Add intent-aware verifier checks before loosening context selection.

Acceptance criteria:

- timing answers require timing evidence
- explanation answers require cited factor evidence
- remedy answers cannot imply guaranteed removal
- unsupported timing certainty fails verification
- section-level violation reporting exists

### Phase 3: Deterministic Context Planner

Add config-driven domain + intent planning.

Acceptance criteria:

- planner output is typed
- every configured domain has required context by intent
- planner failure falls back to full deterministic bundle
- no model-selected context

### Phase 4: Structured UI Renderer

Upgrade frontend rendering for Ask v2 schema.

Acceptance criteria:

- no raw markdown overflow
- acknowledgment, context, interpretation, summary, guidance render separately
- follow-ups continue the same thread
- old threads still render plainly
- failure states are honest and polished

### Phase 5: Add Domain Agents In Sequence

Recommended order:

1. Career
2. Marriage
3. Wealth
4. Children
5. Health
6. Foreign / relocation
7. Education
8. Family property
9. Spirituality
10. Litigation

Why this order:

It follows likely user traffic and emotional importance while allowing safety-sensitive domains to mature later with stricter guardrails.

### Phase 6: Multi-Domain Synthesis

Add synthesis only when at least two domain agents are mature.

Acceptance criteria:

- router distinguishes ambiguity from explicit multi-domain requests
- registry gates each domain independently
- partial readiness is handled honestly
- synthesis cites both bundles
- verifier checks all cited evidence

### Phase 7: Optional Graph Runtime

Consider LangGraph or similar only when branching/state becomes hard to manage manually.

Use it if we need:

- resumable graph state
- node-level observability
- complex branching
- long-running multi-domain workflows
- human-in-the-loop review

Do not use it merely for architecture fashion.

## Future Ideal

The ideal Siddha Ask system becomes a consultation graph:

```text
User intent
  -> Safety
  -> Domain intelligence
  -> Context planning
  -> Deterministic Vedic computation
  -> Specialist interpretation
  -> Verification
  -> Personalized guidance
  -> Action paths across the app
```

It should eventually connect Ask to:

- Today guidance
- Dashas
- Yantra / transits
- Remedies and practice tracking
- Calendar and muhurta
- Charts and vargas
- Compatibility
- User preferences and persona
- Location-aware panchanga
- Knowledge ingestion and reviewed CE sources

But the order matters. Depth first, then breadth.

## Final Position

Siddha should be agentic, but not chaotic.

The right architecture is not an unconstrained swarm of agents. It is a disciplined consultation graph where every node has a responsibility, every answer has evidence, and every claim can be traced back to the Context Engine.

The product promise is:

> Siddha will not merely answer. Siddha will understand, ground, interpret, protect, and guide.

