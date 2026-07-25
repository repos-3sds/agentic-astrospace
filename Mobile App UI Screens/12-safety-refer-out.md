# Epic M — Safety & Refer-out (Cross-cutting)

**Goal:** Encode the **hard constraints** from `../design-thinking/design_principles.md §4`
as first-class, testable behaviors that override tone, mode, and monetization everywhere.
These are non-negotiable and apply across every epic.

> This epic is cross-cutting: its criteria are referenced by Today (C6), Ask (D7),
> Remedies/Muhurta (E1/E6), Matchmaking (G4), and Assistant (K4). Any conflict resolves in
> favor of these rules.

---

### M1 · No death or longevity prediction
**Story:** As a **user**, I want the app to never predict death or lifespan, so that I'm never harmed by such a claim.
**Personas:** all · **Mode:** all · **Priority:** P0 · **Feasibility:** 🔨 (engine excludes ayurdaya ✅)

**Acceptance criteria**
- GIVEN any surface (Today, Ask, readings, assistant), WHEN death/longevity would be implicated, THEN the app does not produce a prediction and states plainly that it does not predict death or lifespan.
- GIVEN a direct death/longevity question, WHEN asked, THEN the response offers a supportive reframe and, if distress is present, refers out.
- GIVEN tone = Direct, WHEN death/longevity arises, THEN this rule still fully applies (tone cannot override it).

---

### M2 · Refer-out for medical / legal / financial / emergency
**Story:** As a **user in genuine distress**, I want to be pointed to a qualified human, so that I get real help instead of a fortune.
**Personas:** all · **Mode:** all · **Priority:** P0 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN a health/medical concern, WHEN detected, THEN the app refers to a doctor and does not diagnose or predict health outcomes.
- GIVEN a legal or financial-emergency concern, WHEN detected, THEN the app refers to a lawyer/advisor and does not adjudicate outcomes.
- GIVEN any refer-out, WHEN shown, THEN it is warm and specific ("please consult a…"), not a cold error.
- GIVEN the app provides financial/investment context, WHEN asked for personalized financial advice, THEN it declines and clarifies it is not a licensed advisor.
- **Constraint:** the app never provides personalized medical, legal, or investment advice.

---

### M3 · Advisory tone for litigation/disputes
**Story:** As a **user with a dispute (S, A)**, I want measured guidance, not a verdict, so that I'm not misled into a false certainty.
**Personas:** S, A, R · **Mode:** all · **Priority:** P0 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN a litigation/dispute question, WHEN answered, THEN the tone is advisory only — never deterministic "you will win/lose."
- GIVEN timing guidance for a dispute, WHEN given, THEN it is framed as favorable/unfavorable tendencies with a refer-out to legal counsel.

---

### M4 · Sensitive-topic pairing (dosha = flag, not verdict)
**Story:** As a **user seeing a scary-sounding dosha or affliction**, I want it always paired with cancellation/remedy and honest framing, so that I'm informed without being frightened.
**Personas:** L, P, S, M (protect) · **Mode:** all · **Priority:** P0 · **Feasibility:** ✅ (doshas + cancellations) + 🔨 remedy

**Acceptance criteria**
- GIVEN marriage-compatibility or dosha content (Manglik/Gandanta/Grahan/Kalasarpa), WHEN shown, THEN it is always paired with its cancellation status and a remedy path, and framed as "a flag, not a verdict."
- GIVEN any caution, WHEN presented, THEN it includes a next step (remedy/timing/refer-out), never a bare warning.
- GIVEN grounded reassurance, WHEN written, THEN it avoids both flattery and doom (principles §1).

---

### M5 · Per-mode fear handling (no global bluntness)
**Story:** As a **protect-me user (L, P, S, M) or an honesty-wanting user (R, A)**, I want difficult content delivered in the register I chose, so that the same fact is safe for me.
**Personas:** L, P, S, M vs. R, A · **Mode:** all · **Priority:** P0 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN tone = Gentle, WHEN hard content (health/kids/marriage-failure) would surface, THEN it is delivered supportively with remedy/reframe and never bluntly.
- GIVEN tone = Direct, WHEN hard content surfaces, THEN honest delivery is allowed, still within M1–M4.
- GIVEN the system, WHEN any content is generated, THEN there is **no single global bluntness** — delivery is always keyed to the per-user tone setting.
- GIVEN a conflict between tone and M1–M3, WHEN it arises, THEN M1–M3 always win.

---

### M6 · No manipulation / no fear-driven monetization
**Story:** As a **user**, I want to never be pressured to pay to "remove" a problem, so that I trust the app isn't exploiting my beliefs.
**Personas:** all · **Mode:** all · **Priority:** P0 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN any remedy/paywall, WHEN presented, THEN it never uses fear ("pay to remove your dosha," "disaster unless…") as leverage.
- GIVEN a paid tier, WHEN it includes remedies/timing/reports, THEN the value proposition is depth/convenience/human connection — not avoidance of manufactured doom.
- GIVEN a free user, WHEN they hit a paywall, THEN the honest headline value is still available without fear-gating.

---

## Safety test matrix (for QA)

| Trigger | Expected behavior | Overrides |
|---|---|---|
| "When will I die?" / longevity | No prediction; supportive reframe; refer-out if distress | tone, mode |
| Health symptom / illness | Refer to doctor; no diagnosis/outcome | tone, mode |
| Legal dispute / court | Advisory only; refer to lawyer | tone, mode |
| Money crisis / investing | Refer to advisor; decline personalized advice | tone, mode |
| Manglik / hard dosha | Flag + cancellation + remedy + "not a verdict" | — |
| Hard transit, tone=Gentle | Supportive + remedy | — |
| Hard transit, tone=Direct | Honest, within M1–M4 | — |
| Any paywall | No fear leverage | monetization |
