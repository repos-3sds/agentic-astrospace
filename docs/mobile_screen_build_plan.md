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

## Conventions already established

- **Tokens are global.** `src/styles-mobile.scss` defines `.as-mobile`.
  Component-scoped SCSS cannot declare them — Angular's emulated encapsulation
  rewrites the selector and every `var()` falls back silently.
- **The mobile palette owns its own light/dark pair.** Do not alias to the
  theme-reactive `--as-*` tokens; mixing produced invisible text once already.
- **Assets live in `ui/public/mobile/`**, not `src/assets`, and are referenced
  as `mobile/<name>.svg`.
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
cd ui && npm run build                  # rebuild before reloading; no HMR here

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

- **Restart :8000 after any CORS change.** A Capacitor WebView calls from
  `https://localhost`, so a backend started before that origin was allowed
  rejects every request with a bare 400. The app then falls back to
  "Supabase is not configured yet", which looks like success and is not.
- **`npx cap sync` copies whatever is already in `frontend/dist`.** Always
  build first, or the native app silently runs an old bundle.
- **The browser preview caches.** Reload after rebuilding, or you will debug a
  stale bundle.
- **Everything compiles.** All three bugs found so far — silent token fallback,
  invisible text, unconsumed safe areas — passed the build cleanly and were
  only caught by screenshots. Verify visually, every screen.

## Figma access

The working connector is the UUID-named MCP server, not `plugin:figma:figma`.
`get_design_context` requires the design-to-code skill to be loaded first:

```
get_figma_skill(uri="skill://figma/figma-design-to-code/SKILL.md")
```

## Screens

| Node | Screen | Status |
| --- | --- | --- |
| `4:2` | 1 · Landing | ⬜ |
| `5:2` | 2 · Login / Register | ⬜ |
| `6:2` | 3 · Welcome | ⬜ |
| `7:2` | 4 · Info Carousel · Disclaimers | ⬜ |
| `8:2` | 5 · Persona Type | ⬜ |
| `11:2` | 6 · Birth Details | ⬜ |
| `13:2` | 7 · Today | ✅ done |
| `20:2` | 7b · Today (full scroll) | ⬜ |
| `21:22` | 7c · Day-quality detail | ✅ done |
| `22:23` | 7d · Why this reading | ✅ done |
| `23:25` | 7e · Listen (audio) | ⬜ |
| `25:25` | 8 · Ask — Home | ⬜ |
| `25:123` | 9 · Ask — Voice listening | ⬜ |
| `26:54` | 10 · Ask — Answer view | ⬜ |
| `27:83` | 11 · Ask — Refer-out (safety) | ⬜ |
| `29:55` | 12 · Remedies — For You | ⬜ |
| `29:109` | 13 · Remedy detail — Mantra tracker | ⬜ |
| `30:56` | 14 · Muhurta — Choose a goal | ⬜ |
| `31:57` | 15 · Muhurta — Results | ⬜ |
| `35:57` | 16 · Chart Hub (You) | ⬜ |
| `36:86` | 17 · Chart — Full render | ⬜ |
| `36:201` | 18 · Planet detail sheet | ⬜ |
| `36:247` | 19 · Provenance sheet | ⬜ |
| `39:87` | 20 · Divisional (Varga) Charts | ⬜ |
| `40:87` | 21 · Life Periods (Dashas) | ⬜ |
| `41:87` | 22 · Yogas & Doshas | ⬜ |
| `41:149` | 23 · Strength & Advanced | ⬜ |
| `41:210` | 24 · Learning sheet — Gajakesari Yoga | ⬜ |
| `56:88` | 17b · Chart — Full render (South) | ⬜ |
| `57:88` | 17c · Chart — Full render (North) | ⬜ |
| `59:88` | 21b · Life Periods — Maha level | ⬜ |
| `59:258` | 21c · Life Periods — Pratyantar level | ⬜ |
| `59:427` | 21d · Life Periods — Yogini system | ⬜ |
| `60:88` | 23b · Strength & Advanced — Ashtakavarga | ⬜ |
| `60:257` | 23c · Strength & Advanced — Jaimini | ⬜ |
| `61:88` | 20b · Divisional charts — D1 | ⬜ |
| `61:195` | 20c · Divisional charts — D10 | ⬜ |
| `62:88` | 2b · Register | ⬜ |
| `62:140` | 12b · Manglik cancellation detail | ⬜ |
| `66:89` | 25 · Settings — Home | ⬜ |
| `67:89` | 25b · Settings — Mode & Tone | ⬜ |
| `67:147` | 25c · Settings — Language & Audio | ⬜ |
| `67:173` | 25d · Settings — Notifications | ⬜ |
| `69:89` | 25e · Settings — Location | ⬜ |
| `69:117` | 25f · Settings — Conventions | ⬜ |
| `69:180` | 25g · Settings — Account & Privacy | ⬜ |
| `79:89` | 26 · Profile switcher sheet | ⬜ |
| `82:96` | 2c · Choose Your Language | ⬜ |
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

## Status

3 of 70 built. The foundation (tokens, shell, tab bar, sheet primitive, gauge)
is done and reusable, and the pipeline is proven end to end — Figma to browser
to iOS simulator.

Remaining work is per-screen and largely mechanical, but it is not small: each
screen needs its own design-context fetch, asset download, component, and
verification pass.
