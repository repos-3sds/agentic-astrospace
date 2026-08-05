# Agent A Backend Contracts — 2026-08-06

**Status:** point-in-time delivery log for the Agent A slice of
[practitioner_epics_user_stories_2026-08-06.md](practitioner_epics_user_stories_2026-08-06.md)
Sprint 1 (US-PR-003, US-PR-011, US-PR-013). Written for the mobile agent
(Agent B) to consume without re-reading the diff. Jaimini's validation
detail lives in its own doc — see
[jaimini_validation_2026-08-06.md](jaimini_validation_2026-08-06.md) — this
file covers the remedy contract and the yoga/dosha KB schema.

## 1. Remedy recommendation contract (US-PR-003)

`GET /api/v1/remedies/{kundli_id}` — implementation in
[astrospace/core/vedic/remedies.py](../astrospace/core/vedic/remedies.py),
thin router in
[astrospace/api/remedy_routes.py](../astrospace/api/remedy_routes.py).
Tests: [tests/test_remedies_muhurta.py](../tests/test_remedies_muhurta.py)
(`TestRemedies`, 21 tests) and
[tests/test_mobile_routes.py](../tests/test_mobile_routes.py)
(`TestRemedyRoutes`).

### What changed

- **Manglik no longer appears as a generic remedy card.** `afflictions()`
  and `recommend()` both take `include_manglik: bool = False`; the route
  exposes it as a query param, default `false`. Only a caller building a
  compatibility/dosha-detail screen should pass `include_manglik=true`.
  Gandanta and grahan are unaffected — they were never the problem the audit
  flagged, only Manglik was.
- Every group now carries the full contract: `recommendation_id` (stable,
  independent of detection order — e.g. `dasha-mahadasha-saturn`,
  `dignity-debilitated-mercury`, `dosha-manglik`), a structured `trigger`
  object, `reason_short` / `reason_practitioner`, `evidence` (the raw
  computed data behind the reason — dasha period dates, dignity/sign,
  combustion orb, or the full dosha detail dict), `source_status`,
  `tradition_source`, `convention_dependent`, `safety_note`, an integer
  `priority` (1 = most relevant, matching detection order: active dasha >
  dosha > debilitation > combustion), and `practices`.
- Each practice: `practice_slug`, `type` (was `remedy_type` in the old
  per-kundli response — **renamed**, do not confuse with `catalog()`'s
  `remedy_type`, which is unchanged because it feeds the `remedies` DB table
  column directly), `title`, `instructions`, `cadence`, `target_count`,
  `preferred_day`, `optional_cost`, and — for mantra practices only — an
  `audio` block.

### `source_status` per trigger kind

| kind | source_status | why |
| --- | --- | --- |
| `dasha` | `verified_common` | deterministic Vimshottari computation, not a convention choice |
| `dignity` (debilitation) | `verified_common` | the 7th-from-exaltation debilitation rule is undisputed |
| `combustion` | `convention_dependent` | orb thresholds vary by text/software (see `strength.COMBUSTION_ORBS`) |
| `dosha` (manglik/gandanta/grahan) | whatever `doshas.py`'s own `enrich_rule_result` already says | passed through, not re-derived |

### Audio metadata — honest placeholder, not a fabricated asset

Every mantra practice's `audio` block has real `text`/`transliteration`
(the mantra itself) and `count_target` (108), but `audio_url: null` and
`audio.source_status: "pending_assets"`. **No recorded audio exists yet.**
This is a deliberate "pending" state per CLAUDE.md's evidence-based rule —
do not have the client fabricate a path or treat `null` as an error; treat
it as "text-only for now, wire up playback when assets land."

### What the mobile agent can build on this immediately

- `/m/remedies` can call the endpoint directly — the "reconstructs cards
  from `dashas()` and `yogasDoshas()`" gap the audit flagged is now backend
  work, not something the client needs to keep doing.
- `recommendation_id` is stable across requests for the same chart state —
  safe to use as the streak/reminder key (`remedy_slug + kundli_id` from the
  epic maps directly to `practice_slug + kundli_id`, or
  `recommendation_id + practice_slug + kundli_id` if you need to
  disambiguate which trigger led to a given practice being started).
- Manglik detail belongs on a Compatibility/Dosha-detail screen calling with
  `include_manglik=true`; do not add a client-side Manglik card by
  re-deriving it from `/yogas-doshas` — that recreates the exact bug this
  pass fixed.
- `catalog()` / `GET /api/v1/remedies/catalog` is unchanged in shape (still
  `slug`/`remedy_type`) because it seeds the `remedies` DB table — don't
  expect `practice_slug`/`type` there, only in the per-kundli response.

## 2. Yogas/Doshas KB schema expansion (US-PR-013)

[astrospace/knowledge/vedic_rules/yogas.json](../astrospace/knowledge/vedic_rules/yogas.json)
(27 rules) and
[doshas.json](../astrospace/knowledge/vedic_rules/doshas.json) (5 rules, 2
`not_implemented`) now carry, per rule: `classical_name` (new — see below),
`category`, `rule` (exact trigger), `status` (source_status),
`implementation`, `source_refs`, `practitioner_explanation`,
`lay_explanation`, `strength_rubric`, `caveats` (structured list — new),
and `notes` (freeform, unchanged). Schema is enforced by
[tests/test_vedic_rules_kb.py](../tests/test_vedic_rules_kb.py).

### `classical_name` vs `name`

A computed result's `name` can be per-instance (`"Raja Yoga: Sun-Moon"`,
`"Neecha Bhanga for Saturn"`). `classical_name` is always the general
classical term from the KB (`"Raja Yoga"`, `"Neecha Bhanga Raja Yoga"`) —
the string a "Learn this Yoga" sheet (US-PR-014) should title itself with,
regardless of which specific instance the user tapped.

### Where the new fields show up

Both places, not one:

1. **Inline on every computed yoga/dosha result** — `yoga_summary()` and
   `dosha_summary()` already route every result through
   `enrich_rule_result()`, which now merges `classical_name`,
   `practitioner_explanation`, `lay_explanation`, `strength_rubric`,
   `caveats` into the same payload the chart already returns from
   `/{kundli_id}/yogas`, `/{kundli_id}/doshas`, `/{kundli_id}/yogas-doshas`.
   **No new API call is required to render "what this yoga means, why the
   tag is mild/moderate/strong, and any cancellation" directly on the
   card** — it's already in the response you're getting today.
2. **A standalone reference catalog** — new endpoints
   `GET /api/v1/vedic/rules` (optional `?kind=yoga|dosha`) and
   `GET /api/v1/vedic/rules/{rule_id}` in
   [astrospace/api/vedic_routes.py](../astrospace/api/vedic_routes.py), for
   a "browse all yogas/doshas" reference screen or a "Learn this Yoga" sheet
   that wants the full catalog rather than parsing it out of a chart
   response. Both are public (no kundli ownership check — this is static
   reference data, not user data). Unknown `rule_id` returns `200` with a
   `status: "needs_review"` pending shape rather than a `404`, so the client
   never has to special-case a missing rule.

### Strength rubrics are transcribed from the actual code, not invented

Every `strength_rubric` string was written by reading the corresponding
function in
[astrospace/core/vedic/yogas.py](../astrospace/core/vedic/yogas.py) — e.g.
Gajakesari's "strong if house 1 from Moon else moderate, shifted by
debilitation/exaltation" is `_gajakesari()` + `_dignity_adjusted()` in
prose, not a guess. If the code changes, the KB prose will drift — there is
no automated check tying the two together yet; a future pass could assert
the rubric text against the actual `strength` values a synthetic chart
produces, the way `test_vedic_rules_kb.py` currently only checks shape, not
content-accuracy.

### Caveats vs notes

`caveats` is new and structured (a plain list of strings — cancellation
rules, convention choices, known implementation gaps). `notes` is unchanged
and still carries the same freeform commentary it always did (some content
now overlaps between the two by design — e.g. a cancellation rule may
appear in both — since `notes` is what already flows into computed results
today and `caveats` is the more legible surface for a UI to render as a
distinct "caveats" list rather than parsing prose).

## 3. What's explicitly still open for a future pass

- Yoga/dosha `strength_rubric` accuracy is not machine-verified against the
  actual computation (see above).
- Jaimini rules are not yet in this KB (`chara_karakas`/`arudha_padas` have
  no `rule_id` and don't route through `enrich_rule_result`) — reasonable
  next step once Jaimini UI prominence increases (US-PR-012), out of scope
  for this pass.
- `pitru_dosha` and `sarpa_dosha` remain `not_implemented`; do not build UI
  affordances for them.
- No stronger-lord variant for the Scorpio/Aquarius dual-lordship
  convention (see jaimini_validation doc).
