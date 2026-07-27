# Mobile Screen Build Plan

Implementation tracker for the designed native app. Source of truth is the
Figma file `RRhuTcaKIhqILZW7JUKFzI` (page `0:1`); node IDs below are what
`get_design_context` takes, so a screen can be picked up without re-deriving
anything.

## How to build one

```
1. get_design_context(fileKey=RRhuTcaKIhqILZW7JUKFzI, nodeId=<node>)
2. Download any new exported assets into ui/public/mobile/
3. Build under ui/src/app/features/mobile/<screen>/ using the tokens in
   src/styles-mobile.scss and the mixins in features/mobile/mobile-tokens.scss
4. Route it under /m, verify in the browser at 375x812, screenshot
5. Re-verify natively: npm run build:native:dev, then rebuild in Xcode
```

## The two front ends do not meet

`/m/*` is guarded off the production web build by `nativeAppGuard`
(`core/native-app.guard.ts`). A production web visitor who types `/m` is sent
to `/`; native always passes, and so does any non-production build, which is
what keeps the browser verification loop alive.

This is a visibility boundary, not a security one — the mobile code still ships
in the bundle. Excluding it outright means a second build configuration, which
is a bigger change than the problem needs.

## Conventions already established

- **Tokens are global.** `src/styles-mobile.scss` defines `.as-mobile`.
  Component-scoped SCSS cannot declare them — Angular's emulated encapsulation
  rewrites the selector and every `var()` falls back silently.
- **The mobile palette owns its own light/dark pair.** Do not alias to the
  theme-reactive `--as-*` tokens; mixing produced invisible text once already.
- **Assets live in `ui/public/mobile/`**, not `src/assets`, and are referenced
  as `mobile/<name>.svg`.
- **One asset per glyph, not per size.** Figma exports a chevron at 16, 17, 18
  and 20px as four files, but they are one vector scaled — path and stroke both
  scale proportionally, and SVG scales losslessly. Diff a new export against the
  one you have before adding it, and size the leaf in CSS. Different *colour* is
  a different asset (`play.svg` vs `play-muted.svg`); different size is not.
- **Sheets use `as-sheet`** for scrim, radius, handle and safe-area padding.
- **Exported assets are used as-is.** The only exception so far is the day
  gauge, whose arc is data-driven and so is redrawn from the export's geometry.
- **Safe areas** are consumed by the shell; screens should not re-apply them.

## Running and verifying

Two backends, and the difference matters:

| Port | Config | Auth | Use for |
| --- | --- | --- | --- |
| 8000 | `astrospace` | Supabase **enabled** — needs a bearer token | the native app |
| 8010 | `astrospace-debug` | dev bypass, SQLite | browser verification |

```bash
# browser (fastest loop) — serves the built SPA
preview_start name=astrospace-debug     # -> http://localhost:8010/m/today
cd ui && npm run build:dev              # rebuild before reloading; no HMR here

# native
cd ui && npm run build:native:dev       # dev config + cap sync
cd ui/ios/App && xcodebuild -project App.xcodeproj -scheme App \
  -destination "platform=iOS Simulator,id=<udid>" \
  -configuration Debug -skipMacroValidation -derivedDataPath /tmp/astrospace-dd build
# then: control launch app_path=/tmp/astrospace-dd/Build/Products/Debug-iphonesimulator/App.app
```

The simulator needs device access granted once per session ("Let Claude use it"
on the panel), otherwise screenshots and the build tool's device lookup both
fail with a misleading "no booted simulator".

## Traps already hit — do not rediscover

- **~~Restart :8000 after any CORS change.~~ Fixed structurally — no longer a
  step.** A Capacitor WebView calls from `https://localhost`, so every API
  request is cross-origin. This used to mean a backend started before that
  origin was allowed rejected everything with a bare 400, which the app
  reported as "Supabase is not configured yet" — a CORS failure wearing a
  config failure's clothes. `main.py` now appends `_NATIVE_ORIGINS` after
  `ALLOWED_ORIGINS` unconditionally (f73e882), so a production allowlist can no
  longer drop them, and `tests/test_cors_origins.py` holds that. Restarting
  proves nothing; if you suspect CORS, ask the running server:

  ```bash
  curl -s -D- -o /dev/null -H "Origin: https://localhost" http://127.0.0.1:8000/api/v1/health | grep -i access-control-allow-origin
  ```

  An `access-control-allow-origin: https://localhost` in the response means the
  origin is live and the problem is somewhere else.
- **Verify with `npm run build:dev`, not `npm run build`.** `ng build` defaults
  to the *production* configuration, and `/m` is guarded off the production web
  build (see below) — so a production build serves the web landing page at
  `/m/today` and every screen looks deleted. Nothing is wrong; you built the
  wrong config.
- **`npx cap sync` copies whatever is already in `frontend/dist`.** Always
  build first, or the native app silently runs an old bundle.
- **The browser preview caches.** Reload after rebuilding, or you will debug a
  stale bundle.
- **The web app's global CSS still matches mobile elements.** Angular's view
  encapsulation scopes *your* rules; it does not stop a global rule in
  `styles.scss` from matching your markup. `class="hero"` on Ask picked up the
  web app's `@media (max-width: 599px)` glass card and rendered the heading on a
  dark slab. Before naming a class, check it:

  ```bash
  grep -n '\.your-class\b' ui/src/styles.scss
  ```

- **A screen routed outside the shell paints nothing.** The shell set the
  background on its own `:host`, so every screen inside it was fine — the first
  screen routed outside it (onboarding) inherited the *web app's* theme-reactive
  background and rendered `--m-text`, a near-black, on the dark theme. The
  headline was invisible. `.as-mobile` now sets `background`/`color` itself, so
  carrying the class is enough; keep it that way.
- **Everything compiles.** All four bugs found so far — silent token fallback,
  invisible text, unconsumed safe areas, and the global-class collision above —
  passed the build cleanly and were only caught by screenshots. Verify visually,
  every screen.

## Before a device build

`nativeApiOrigin` is now set in both environments, so nothing is outstanding
for a *simulator* build. One thing is still outstanding for a **production**
one:

**The deployed service rejects the Capacitor origin** — it is running an image
built before `https://localhost` was allowed. Confirmed:

```
OPTIONS https://agentic-astrospace-cwuqybpnzq-el.a.run.app/api/v1/auth/config
Origin: https://localhost   ->   HTTP 400
```

**The fix is a redeploy, and nothing else.** The native origins are no longer
part of the configurable set: `main.py` always appends them, whatever
`ALLOWED_ORIGINS` says. So any routine deploy resolves this permanently, and no
future change to `ALLOWED_ORIGINS` can break native again.

Do *not* work around it with `--set-env-vars`. That was the original trap:
`ALLOWED_ORIGINS` replaces the dev defaults, so while the native origins lived
alongside them, pointing it at a production domain silently dropped native
support. `tests/test_cors_origins.py` pins this down.

## Figma access

The working connector is the UUID-named MCP server, not `plugin:figma:figma`.
`get_design_context` requires the design-to-code skill to be loaded first:

```
get_figma_skill(uri="skill://figma/figma-design-to-code/SKILL.md")
```

## Screens

| Node | Screen | Status |
| --- | --- | --- |
| `4:2` | 1 · Landing | ✅ done — `/m/start` |
| `5:2` | 2 · Login / Register | ✅ done — `/m/auth` |
| `6:2` | 3 · Welcome | ✅ done |
| `7:2` | 4 · Info Carousel · Disclaimers | ✅ done |
| `8:2` | 5 · Persona Type | ✅ done |
| `11:2` | 6 · Birth Details | ✅ done |
| `13:2` | 7 · Today | ✅ done |
| `20:2` | 7b · Today (full scroll) | ✅ done — same component as `13:2`, scrolled |
| `21:22` | 7c · Day-quality detail | ✅ done |
| `22:23` | 7d · Why this reading | ✅ done |
| `23:25` | 7e · Listen (audio) | ✅ done — sheet over Today |
| `25:25` | 8 · Ask — Home | ✅ done |
| `25:123` | 9 · Ask — Voice listening | ✅ done — overlay from Ask's mic |
| `26:54` | 10 · Ask — Answer view | ✅ done |
| `27:83` | 11 · Ask — Refer-out (safety) | ✅ done — `?domain=health\|legal\|money\|death` |
| `29:55` | 12 · Remedies — For You | ✅ done — `/m/remedies` |
| `29:109` | 13 · Remedy detail — Mantra tracker | ✅ done — `/m/remedies/mantra` |
| `30:56` | 14 · Muhurta — Choose a goal | ✅ done — `/m/muhurta` |
| `31:57` | 15 · Muhurta — Results | ✅ done — `/m/muhurta/results` |
| `35:57` | 16 · Chart Hub (You) | ✅ done — `/m/chart` |
| `36:86` | 17 · Chart — Full render | ✅ done — `/m/chart/full`, Eastern only |
| `36:201` | 18 · Planet detail sheet | ✅ done |
| `36:247` | 19 · Provenance sheet | ✅ done |
| `39:87` | 20 · Divisional (Varga) Charts | ✅ done — `/m/chart/vargas` |
| `40:87` | 21 · Life Periods (Dashas) | ✅ done — `/m/chart/periods` |
| `41:87` | 22 · Yogas & Doshas | ✅ done — `/m/chart/yogas` |
| `41:149` | 23 · Strength & Advanced | ✅ done — `/m/chart/strength` |
| `41:210` | 24 · Learning sheet — Gajakesari Yoga | ✅ done |
| `56:88` | 17b · Chart — Full render (South) | ⬜ |
| `57:88` | 17c · Chart — Full render (North) | ⬜ |
| `59:88` | 21b · Life Periods — Maha level | ✅ done — `/m/chart/periods` Maha tab |
| `59:258` | 21c · Life Periods — Pratyantar level | ✅ done — `/m/chart/periods` Pratyantar tab |
| `59:427` | 21d · Life Periods — Yogini system | ✅ done — `/m/chart/periods` Yogini tab |
| `60:88` | 23b · Strength & Advanced — Ashtakavarga | ✅ done — Ashtakavarga tab |
| `60:257` | 23c · Strength & Advanced — Jaimini | ✅ done — Jaimini tab |
| `61:88` | 20b · Divisional charts — D1 | ⬜ |
| `61:195` | 20c · Divisional charts — D10 | ⬜ |
| `62:88` | 2b · Register | ✅ done — `/m/auth?mode=register` |
| `62:140` | 12b · Manglik cancellation detail | ✅ done — shared from Chart and Remedies |
| `66:89` | 25 · Settings — Home | ✅ done — `/m/settings`, the More tab |
| `67:89` | 25b · Settings — Mode & Tone | ⬜ |
| `67:147` | 25c · Settings — Language & Audio | ⬜ |
| `67:173` | 25d · Settings — Notifications | ⬜ |
| `69:89` | 25e · Settings — Location | ⬜ |
| `69:117` | 25f · Settings — Conventions | ⬜ |
| `69:180` | 25g · Settings — Account & Privacy | ⬜ |
| `79:89` | 26 · Profile switcher sheet | ⬜ |
| `82:96` | 2c · Choose Your Language | ✅ done — `/m/language` |
| `91:89` | 27 · Gochara (plain transits) | ⬜ |
| `92:89` | 27b · Full Transits | ⬜ |
| `93:89` | 28 · Calendar | ⬜ |
| `94:118` | 29 · Festival detail sheet | ⬜ |
| `97:119` | 30 · Compatibility Hub | ⬜ |
| `97:144` | 30b · Add Prospect | ⬜ |
| `98:119` | 30c · Gun Milan Results | ⬜ |
| `108:92` | 7-dark · Today (Dark mode) | ⬜ |
| `108:186` | 8-dark · Ask Home (Dark mode) | ⬜ |
| `108:246` | 16-dark · Chart Hub (Dark mode) | ⬜ |
| `108:417` | States · Ask — Loading (computing answer) | ⬜ |
| `110:121` | States · Compatibility — Empty (no checks yet) | ⬜ |
| `110:153` | States · Generic — Something went wrong | ⬜ |
| `113:122` | 31 · Readings & Accuracy | ⬜ |
| `114:124` | 31b · Prediction Claims (accuracy) | ⬜ |
| `115:124` | 32 · Notes | ⬜ |
| `116:124` | 28b · Calendar — Day detail (timing feed) | ⬜ |
| `117:124` | 33 · Practitioner Reference | ⬜ |
| `117:175` | 33b · Avkahada & Ghatak | ⬜ |
| `118:124` | 33c · Graha positions & conditions | ⬜ |
| `118:239` | 33d · Ashtakavarga tables | ⬜ |
| `118:383` | 33e · Favourable points | ⬜ |

## Not yet wired

Ask's composer routes every question to the answer view (26:54), including
ones that must refer out. Choosing between 26:54 and 27:83 is the answer
pipeline's call — classifying intent in the client would put the safety
boundary somewhere that can be bypassed. Both screens exist and are routed;
the decision lands with `/api/v1/ask`.

## Status

36 of 70 built: M1's Today set, the complete authentication/onboarding entrance, all of M3 Ask, M4 Remedies, M5 Muhurta and
the M6 Chart flow (hub -> full render -> planet detail -> provenance -> divisional charts -> life periods). The foundation (tokens, shell,
tab bar, sheet primitive, gauge, Ask composer, evidence sheet) is done and
reusable, and the pipeline is proven end to end — Figma to browser to iOS
simulator.

Remaining work is per-screen and largely mechanical, but it is not small: each
screen needs its own design-context fetch, asset download, component, and
verification pass.
