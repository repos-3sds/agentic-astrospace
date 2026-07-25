# Design Thinking — AstroSpace

Context pack for UX / design-thinking work. Hand these to a designer or a
design-thinking agent **in the order listed** — who/why/rules first, then what
exists, then deep reference.

## Read in this order

1. **product_brief.md** — vision, market, the two-persona / experience-mode strategy, what we're missing.
2. **design_principles.md** — tone, trust, fear-handling per mode, safety exclusions, language/accessibility.
3. **persona.md** — the 7 users we design for (synthetic proxy until real survey data lands).
4. **capabilities.md** — what the engine can compute today vs not-yet (design material + feasibility).
5. **ux_current_state.md** — the actual screens/IA today, so redesign starts from reality.
6. **context_engine_taxonomy.md** — the 10 life-domains the engine can speak to.
7. **astrology_survey.md** — the research instrument that will replace the synthetic personas.
8. **full_astro_software_checklist.md** — feature landscape (built vs not).
9. **mobile_app_plan.md** — current-state mobile UX findings + prior mobile plan (implementation-heavy; skim).

## What's in this folder vs. referenced

**Local in `design-thinking/`:**
- README.md, product_brief.md, design_principles.md, capabilities.md,
  ux_current_state.md — the new synthesis docs.
- persona.md — the 7 personas.
- ideation_native_app.md — divergent ideation for the native iOS/Android reimagining
  (draw-from brainstorm, persona-anchored + feasibility-tagged; not a spec).

**Canonical in `docs/` (read these there):**
- astrology_survey.md — the research instrument.
- context_engine_taxonomy.md — the 10 life-domains.
- full_astro_software_checklist.md — feature landscape.
- mobile_app_plan.md — mobile UX findings + prior plan.

> These four were not mirrored into this folder due to a transient file-read lock at
> creation time; they live in `docs/` and can be copied here later. Nothing is lost.

## Status note

The four synthesis docs (product_brief, design_principles, capabilities,
ux_current_state) are distilled from a deep engineering + product survey of the
codebase conducted over the build sessions — a *fresh* re-survey was blocked this
session by a sandbox read lock, so reconcile the product_brief positioning against
`VISION.md` / `README.md` when convenient. Treat the personas and any
willingness-to-pay / preference claims as **synthetic proxy** until validated with
real survey responses.
