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
- Run the suite with `.venv/bin/python -m pytest tests/ -q` (1540 passing).
  Frontend: `cd ui && npx ng test --watch=false --browsers=ChromeHeadless`.
- Work deliberately left unbuilt goes in **one** backlog — the "Deferred
  backlog" section of
  [docs/backend_astro_depth_checklist_2026-08-06.md](docs/backend_astro_depth_checklist_2026-08-06.md),
  which is the living tracker for engine + KB depth. Each entry states why
  it isn't built, what would unblock it, and where the code hook is, so
  picking one up doesn't mean re-deriving the research. Add deferrals there
  rather than starting a new doc or leaving them in a commit message.

## Docs state their own status

Every markdown file declares what it is in its first three lines — `canonical`,
`source of truth`, `point-in-time audit`, or `superseded`. Without that, nobody
can tell a live tracker from a finished audit, and both get half-trusted.

Audits are dated and disposable: fold them into one log rather than adding a
file per pass. Five audit documents in three days is how a repo stops being
readable.

Anything not reachable from this file is a candidate for deletion at the next
sweep — but **check for inbound references first**. `docs/mobile_app_plan.md`
looked dead by its date and was cited from three places; `plan.md` looks dead
and holds an open validation commitment that `tests/test_vedic.py` points at.

## Verify visually, not just by build

Every UI bug found while building the native screens compiled cleanly: CSS
custom properties silently falling back, invisible text from mixing
theme-reactive and fixed tokens, safe areas declared but never consumed. A green
build is not evidence that a screen renders. Screenshot it.
