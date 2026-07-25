# Mobile App UI Screens — User Stories & Acceptance Criteria

> Product backlog for the **native iOS/Android reimagining** of AstroSpace.
> Derived from the design-thinking pack (`../design-thinking/`) and the ideation +
> fresh user-flow work. Screens and stories are organized by **epic**; every story is
> persona-anchored, mode-aware, feasibility-tagged, and carries **Gherkin-style
> acceptance criteria**.

## How to read this backlog

Each story follows a fixed template:

```
### <ID> · <Screen / capability name>
Story: As a <persona/role>, I want <capability>, so that <benefit>.
Personas: … · Mode: … · Priority: P0|P1|P2 · Feasibility: ✅|🔨|🌙
Acceptance criteria:
  - GIVEN <context>, WHEN <action>, THEN <observable outcome>.
```

### Legend

**Feasibility** (vs. the calculation engine — see `../design-thinking/capabilities.md`)
- ✅ engine can do it today
- 🔨 new build required
- 🌙 moonshot / later

**Priority**
- **P0** — MVP / activation-critical
- **P1** — core value, fast-follow
- **P2** — depth / delight / later

**Modes** (from `../design-thinking/product_brief.md`) — G = Guided · B = Balanced (default) · Pr = Practitioner

### Personas (from `../design-thinking/persona.md`)

| Tag | Persona | Type | Mode |
|---|---|---|---|
| **L** | Lakshmi — devoted homemaker, Vijayawada | Common | Guided |
| **R** | Ravi — pragmatic skeptic, Hyderabad IT | Common | Balanced |
| **P** | Padma — devout elder, Guntur | Common | Guided |
| **A** | Anand — enthusiast-practitioner, Bengaluru | Expert | Practitioner |
| **S** | Suresh — matchmaking parent, Rajahmundry | Common | Balanced |
| **An** | Ananya — Gen-Z social follower, Bengaluru | Common (not chased) | Guided |
| **M** | Meera — diaspora anchor, USA | Common | Balanced |

## Epic map

| # | File | Epic | Covers |
|---|---|---|---|
| A | [01-onboarding-activation.md](01-onboarding-activation.md) | Onboarding & Activation | Welcome → hook → birth details → mode/tone → cast → the Aha |
| B | [02-authentication-account.md](02-authentication-account.md) | Authentication & Account | Soft gate, sign-in, guest→account merge, deletion |
| C | [03-today-daily-guidance.md](03-today-daily-guidance.md) | Today / Daily Guidance | The home card, day-quality, do/avoid, audio, offline |
| D | [04-ask-question-engine.md](04-ask-question-engine.md) | Ask (question-first) | Text/voice ask, chips, answer template, ask-a-date |
| E | [05-what-to-do-remedies-muhurta.md](05-what-to-do-remedies-muhurta.md) | What to do | Remedies, streaks, goal-based muhurta finder |
| F | [06-chart-practitioner-depth.md](06-chart-practitioner-depth.md) | Chart & Practitioner Depth | Charts, vargas, dashas, AV/Shadbala/Jaimini, learning |
| G/H | [07-matchmaking-and-calendar.md](07-matchmaking-and-calendar.md) | Matchmaking + Calendar | Gun Milan story, match report, festival/observance |
| I | [08-language-audio-accessibility.md](08-language-audio-accessibility.md) | Language, Audio & A11y | Telugu, audio, low-connectivity, WCAG AA |
| J | [09-trust-why-learning.md](09-trust-why-learning.md) | Trust & the "Why" | "Why this reading?", computed badge, honesty labels |
| K | [10-native-platform.md](10-native-platform.md) | Native Platform | Widgets, Live Activities, watch, Siri, notifications, share |
| L | [11-profiles-modes-settings.md](11-profiles-modes-settings.md) | Profiles, Modes & Settings | Multi-profile, comfort dial, tone, open-to, conventions |
| M | [12-safety-refer-out.md](12-safety-refer-out.md) | Safety & Refer-out (cross-cutting) | No death/longevity, refer-out, per-mode fear handling |

## The flow spine (context for the epics)

```
WELCOME ─► HOOK Q ─► BIRTH DETAILS ─► HOW YOU LIKE ANSWERS ─► [cast] ─► THE AHA ─► soft SAVE ─► TODAY
```

Everyone walks the same spine; the flows diverge at only two points — **the mode
question** (Common → Guided/Balanced; Expert → Practitioner) and **the Aha** (Common =
plain signature; Expert = chart workbench). One stable route tree underneath both;
only labels, priority, disclosure, and copy register adapt.

## Traceability

- Vision & positioning → `../design-thinking/product_brief.md`
- Hard constraints (safety, tone, a11y) → `../design-thinking/design_principles.md`
- What's computable today → `../design-thinking/capabilities.md`
- Idea source → `../design-thinking/ideation_native_app.md`

## Status

Draft v1 — synthetic-persona-validated. Willingness-to-pay, Telugu/audio demand, and
the gentle-vs-honest split should be confirmed with real survey responses
(`../docs/astrology_survey.md`) before committing build order.
