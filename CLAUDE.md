# AstroSpace

Vedic astrology, computed. FastAPI + Swiss Ephemeris backend, Angular 20 SPA,
Supabase Postgres. The SPA is served same-origin by FastAPI in production.

## Two front ends, not one

| Path | What it is |
| --- | --- |
| `/` and the rest | the existing responsive **web app** |
| `/m/*` | the **native app** being built from the Figma designs |

They are separate. A route named `today` or `ask` in the web app is *not* the
designed screen of the same name. Building the native app means
`ui/src/app/features/mobile/`, not editing the web tabs.

Native packaging is Capacitor over the same bundle — see
[docs/native_builds.md](docs/native_builds.md). To continue the screen build,
read [docs/mobile_screen_build_plan.md](docs/mobile_screen_build_plan.md) first;
it has every Figma node ID, the per-screen recipe, and the traps already hit.

## Non-negotiables

These are product constraints, enforced in code and tests — see
[design-thinking/design_principles.md](design-thinking/design_principles.md) §4
and §6:

- No death, longevity, or medical/legal/financial verdicts. Those intents refer
  out to a qualified professional instead of being answered.
- A dosha is **a flag, not a verdict**. Never suppress one, never escalate it.
- Anything convention-dependent ships with `is_convention_dependent` and an
  `observance_note`. Amanta vs purnimanta, Ekadashi variants, moonrise fasts and
  Sankranti cut-offs all have more than one defensible answer; state the rule
  used rather than implying false precision.
- Remedies are traditional practice, never "pay to remove".

## Working here

- The astrology lives in `astrospace/core/vedic/`. API routers are thin
  wrappers; do not move computation into them.
- Catalog tables are seeded from the engines, never hand-authored:
  `python -m astrospace.db.seed`.
- `.env` holds real credentials. Never read it into the transcript, never commit
  it, and let the user edit it themselves.
- Run the suite with `.venv/bin/python -m pytest tests/ -q` (650 passing).
  Frontend: `cd ui && npx ng test --watch=false --browsers=ChromeHeadless`.

## Verify visually, not just by build

Every UI bug found while building the native screens compiled cleanly: CSS
custom properties silently falling back, invisible text from mixing
theme-reactive and fixed tokens, safe areas declared but never consumed. A green
build is not evidence that a screen renders. Screenshot it.
